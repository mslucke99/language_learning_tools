import os
import json
import sqlite3
import requests
import gzip
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Generator

class DictionaryManager:
    """
    Manages the lifecycle of local dictionaries:
    - Downloading raw JSONL data from Kaikki.org
    - Converting JSONL to optimized SQLite databases
    - Listing available and installed dictionaries
    """
    
    # Base URL for Kaikki.org downloads (using English edition for broader coverage)
    # Format: kaikki.org-dictionary-{StartLanguage}.jsonl
    KAIKKI_BASE_URL = "https://kaikki.org/dictionary/kaikki.org-dictionary-{}.jsonl"
    
    def __init__(self, data_dir: str = "data/dictionaries"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "dictionaries.db"
        self._init_db()

    def _init_db(self):
        """Initialize the single SQLite database for all languages."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main entries table
        # We index 'word' for fast lookups
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language_code TEXT NOT NULL,
                word TEXT NOT NULL,
                pos TEXT,
                definitions_json TEXT,  -- List of definition strings
                audio_json TEXT,        -- List of audio URLs or objects
                ipa TEXT
            )
        ''')
        
        # Index for fast word lookups per language
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_word_lang 
            ON entries (word, language_code)
        ''')
        
        # Metadata table to track installed dictionaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                language_code TEXT PRIMARY KEY,
                version TEXT,
                install_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def is_language_installed(self, lang_code: str) -> bool:
        """Check if a language is installed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM metadata WHERE language_code = ?", (lang_code,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def download_and_import(self, lang_name: str, lang_code: str, progress_callback=None):
        """
        Download dictionary for a language and import it into SQLite.
        
        Args:
            lang_name: English name of the language (e.g., 'Spanish', 'Korean') used in Kaikki URL.
            lang_code: ISO code (e.g., 'es', 'ko') used for storage.
            progress_callback: Optional function(current, total, status_message)
        """
        url = self.KAIKKI_BASE_URL.format(lang_name)
        jsonl_path = self.data_dir / f"{lang_name}.jsonl"
        
        # 1. Download
        if progress_callback:
            progress_callback(0, 100, f"Downloading {lang_name} dictionary...")
            
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(jsonl_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        except Exception as e:
            if progress_callback:
                progress_callback(0, 0, f"Error downloading: {str(e)}")
            raise e

        # 2. Import to SQLite
        if progress_callback:
            progress_callback(50, 100, f"Processing {lang_name} dictionary...")
            
        self._import_jsonl_to_sqlite(jsonl_path, lang_code)
        
        # 3. Cleanup
        if jsonl_path.exists():
            os.remove(jsonl_path)
            
        if progress_callback:
            progress_callback(100, 100, f"Finished installing {lang_name}.")

    def _import_jsonl_to_sqlite(self, file_path: Path, lang_code: str):
        """Reads JSONL and bulk inserts into SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing entries for this language if any (re-import)
        cursor.execute("DELETE FROM entries WHERE language_code = ?", (lang_code,))
        
        batch_size = 5000
        batch = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Extract fields
                    word = entry.get('word')
                    if not word:
                        continue
                        
                    pos = entry.get('pos')
                    
                    # Extract definitions (senses)
                    definitions = []
                    for sense in entry.get('senses', []):
                        for gloss in sense.get('glosses', []):
                            definitions.append(gloss)
                    
                    # Skip if no definitions
                    if not definitions:
                        continue
                        
                    # Extract Audio/IPA
                    audio_links = []
                    ipa_text = None
                    for sound in entry.get('sounds', []):
                        if 'mp3' in sound:
                            audio_links.append(sound['mp3'])
                        if 'ipa' in sound and not ipa_text:
                            ipa_text = sound['ipa']

                    batch.append((
                        lang_code,
                        word,
                        pos,
                        json.dumps(definitions, ensure_ascii=False),
                        json.dumps(audio_links),
                        ipa_text
                    ))
                    
                    if len(batch) >= batch_size:
                        cursor.executemany('''
                            INSERT INTO entries (language_code, word, pos, definitions_json, audio_json, ipa)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', batch)
                        batch = []
                        
                except json.JSONDecodeError:
                    continue
        
        # Final batch
        if batch:
            cursor.executemany('''
                INSERT INTO entries (language_code, word, pos, definitions_json, audio_json, ipa)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', batch)
            
        # Update metadata
        from datetime import datetime
        cursor.execute('''
            INSERT OR REPLACE INTO metadata (language_code, version, install_date)
            VALUES (?, ?, ?)
        ''', (lang_code, "1.0", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()

class DictionaryEngine:
    """
    Read-only interface for querying the dictionary.
    """
    def __init__(self, db_path: str = "data/dictionaries/dictionaries.db"):
        self.db_path = db_path
        
    def lookup(self, word: str, lang_code: str = None) -> List[Dict]:
        """
        Look up a word. If lang_code is provided, limits to that language.
        Returns a list of dicts: {word, pos, definitions: [], audio: [], ipa}
        """
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM entries WHERE word = ?"
        params = [word]
        
        if lang_code:
            query += " AND language_code = ?"
            params.append(lang_code)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'word': row['word'],
                'pos': row['pos'],
                'definitions': json.loads(row['definitions_json']),
                'audio': json.loads(row['audio_json']) if row['audio_json'] else [],
                'ipa': row['ipa'],
                'lang': row['language_code']
            })
            
        return results
