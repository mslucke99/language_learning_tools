import os
import requests
import logging
from src.core.database import FlashcardDatabase
from src.services.dictionary.dictionary_manager import DictionaryManager

class VocabCalibrationService:
    """
    Handles seeding the known_words table from:
    1. Frequency lists (CEFR levels)
    2. Existing flashcards
    3. Manual definition lookups
    """
    
    # URL pattern for frequency lists from 'frekwencja/most-common-words-multilingual' repo
    # Using raw.githubusercontent.com for direct text access
    # Correct structure: data/wordfrequency.info/{lang}.txt on 'main' branch
    REPO_URL = "https://raw.githubusercontent.com/frekwencja/most-common-words-multilingual/main/data/wordfrequency.info/{lang}.txt"
    
    # Approximate word counts for CEFR levels
    LEVEL_COUNTS = {
        'ABSOLUTE_BEGINNER': 0,
        'INTRODUCTORY': 100,
        'A1': 500,
        'A2': 1500,
        'B1': 3000,
        'B2': 5000,
        'C1': 8000,
        'C2': 12000
    }

    # Map ISO codes to repository specific codes if different
    LANG_MAP = {
        'ko': 'ko',
        'es': 'es',
        'fr': 'fr',
        'ja': 'ja',
        'de': 'de',
        'it': 'it',
        'pt': 'pt',
        'ru': 'ru',
        'zh': 'zh-CN'
    }

    # Human-readable display names for languages
    DISPLAY_NAMES = {
        'ko': 'Korean',
        'es': 'Spanish',
        'fr': 'French',
        'ja': 'Japanese',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'zh': 'Chinese'
    }

    def __init__(self, db: FlashcardDatabase):
        self.db = db
        self.logger = logging.getLogger("VocabCalibration")
        
        # Ensure cache dir exists
        self.cache_dir = os.path.join(os.path.dirname(db.db_path), "cache", "frequency_lists")
        os.makedirs(self.cache_dir, exist_ok=True)

    def calibrate_from_level(self, lang_code: str, level: str, progress_callback=None) -> int:
        """
        Download frequency list and mark top N words as known based on level.
        Returns count of newly added words.
        """
        target_count = self.LEVEL_COUNTS.get(level.upper(), 500)
        
        # Handle absolute beginner (0 words to seed)
        if target_count == 0:
            if progress_callback:
                progress_callback(0, 1, "No frequency words needed for this level.")
                progress_callback(1, 1, "Done!")
            # Mark calibration as done even with 0 words
            self._mark_calibrated(lang_code, level)
            return 0
        
        # 1. Get frequency list
        words = self._get_frequency_list(lang_code)
        if not words:
            self.logger.error(f"Could not fetch frequency list for {lang_code}")
            return 0
            
        # 2. Slice to target usage
        top_words = words[:target_count]
        
        # 3. Bulk insert
        if progress_callback:
            progress_callback(0, target_count, "Seeding vocabulary...")
            
        added = self.db.add_known_words_bulk(top_words, lang_code, source=f"frequency_{level}")
        
        if progress_callback:
            progress_callback(target_count, target_count, "Done!")
        
        # Mark calibration as done
        self._mark_calibrated(lang_code, level)
            
        return added

    def calibrate_from_db(self, lang_code: str) -> int:
        """
        Scan existing flashcards and definitions to mark words as known.
        """
        cursor = self.db.conn.cursor()
        
        # Scan `word_definitions` via join with `imported_content`
        cursor.execute("""
            SELECT wd.word 
            FROM word_definitions wd
            JOIN imported_content ic ON wd.imported_content_id = ic.id
            WHERE ic.language = ?
        """, (lang_code,))
        
        words = [r[0] for r in cursor.fetchall()]
        
        if not words:
            return 0
            
        added = self.db.add_known_words_bulk(words, lang_code, source="flashcard_mining")
        return added

    def _mark_calibrated(self, lang_code: str, level: str):
        """Record that calibration was completed for this language."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO study_settings (setting_key, setting_value)
                VALUES (?, ?)
            """, (f"calibrated_{lang_code}", level))
            self.db.conn.commit()
        except Exception as e:
            self.logger.warning(f"Could not save calibration status: {e}")

    def is_calibrated(self, lang_code: str) -> bool:
        """Check if calibration has been completed for a language."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM study_settings WHERE setting_key = ?",
                (f"calibrated_{lang_code}",)
            )
            row = cursor.fetchone()
            return row is not None
        except Exception:
            return False

    def _get_frequency_list(self, lang_code: str) -> list[str]:
        """Download or read cached frequency list."""
        
        # Repository uses ISO codes directly in data/wordfrequency.info/ (e.g. ko.txt, es.txt)
        # We use LANG_MAP for any non-standard mappings (like zh -> zh-CN)
        mapped_code = self.LANG_MAP.get(lang_code, lang_code)
            
        filename = f"{mapped_code}.txt"
        cache_path = os.path.join(self.cache_dir, filename)
        
        # Check cache
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
                
        # Download
        url = self.REPO_URL.format(lang=mapped_code)
        try:
            print(f"Downloading frequency list from {url}...")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            text = resp.text
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
            return [line.strip() for line in text.splitlines() if line.strip()]
            
        except Exception as e:
            self.logger.error(f"Failed to download frequency list: {e}")
            return []
