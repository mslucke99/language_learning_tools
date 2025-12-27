"""
Study Manager - Handles word definitions and sentence explanations
for imported content from the browser extension.

Features:
- Manage word definitions (user-entered or AI-generated)
- Generate and store sentence explanations
- Integration with Ollama for AI-powered learning
- Language preferences for definitions and explanations
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from database import FlashcardDatabase
from ollama_integration import OllamaClient, OllamaThreadedQuery


class StudyManager:
    """Manages study resources for imported words and sentences."""
    
    def __init__(self, db: FlashcardDatabase, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize the Study Manager.
        
        Args:
            db: FlashcardDatabase instance
            ollama_client: OllamaClient for AI-powered definitions/explanations
        """
        self.db = db
        self.ollama_client = ollama_client
        
        # Get user preferences
        self.native_language = self._get_setting('native_language', 'English')
        self.study_language = self._get_setting('study_language', 'Spanish')
        self.prefer_native_definitions = self._get_setting('prefer_native_definitions', 'true') == 'true'
        self.prefer_native_explanations = self._get_setting('prefer_native_explanations', 'false') == 'true'
    
    # ========== SETTINGS MANAGEMENT ==========
    
    def _get_setting(self, key: str, default: str = '') -> str:
        """Get a study setting value."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT setting_value FROM study_settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default
    
    def _set_setting(self, key: str, value: str):
        """Set a study setting value."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO study_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value)
        )
        self.db.conn.commit()
    
    def set_native_language(self, language: str):
        """Set the user's native language."""
        self._set_setting('native_language', language)
        self.native_language = language
    
    def set_study_language(self, language: str):
        """Set the language being studied."""
        self._set_setting('study_language', language)
        self.study_language = language
    
    def set_definition_language_preference(self, prefer_native: bool):
        """Set whether to prefer native language for definitions."""
        self._set_setting('prefer_native_definitions', 'true' if prefer_native else 'false')
        self.prefer_native_definitions = prefer_native
    
    def set_explanation_language_preference(self, prefer_native: bool):
        """Set whether to prefer native language for explanations."""
        self._set_setting('prefer_native_explanations', 'true' if prefer_native else 'false')
        self.prefer_native_explanations = prefer_native
    
    # ========== IMPORTED CONTENT RETRIEVAL ==========
    
    def get_imported_words(self) -> List[Dict]:
        """Get all imported words with their definition status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT ic.id, ic.content, ic.url, ic.title, ic.created_at, ic.language,
                   COUNT(wd.id) as has_definition
            FROM imported_content ic
            LEFT JOIN word_definitions wd ON ic.id = wd.imported_content_id
            WHERE ic.content_type = 'word'
            GROUP BY ic.id
            ORDER BY ic.created_at DESC
        """)
        
        words = []
        for row in cursor.fetchall():
            words.append({
                'id': row[0],
                'word': row[1],
                'url': row[2],
                'title': row[3],
                'created_at': row[4],
                'language': row[5] or self.study_language,
                'has_definition': row[6] > 0
            })
        return words
    
    def get_imported_sentences(self) -> List[Dict]:
        """Get all imported sentences with their explanation status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT ic.id, ic.content, ic.url, ic.title, ic.created_at, ic.language,
                   COUNT(se.id) as has_explanation
            FROM imported_content ic
            LEFT JOIN sentence_explanations se ON ic.id = se.imported_content_id
            WHERE ic.content_type = 'sentence'
            GROUP BY ic.id
            ORDER BY ic.created_at DESC
        """)
        
        sentences = []
        for row in cursor.fetchall():
            sentences.append({
                'id': row[0],
                'sentence': row[1],
                'url': row[2],
                'title': row[3],
                'created_at': row[4],
                'language': row[5] or self.study_language,
                'has_explanation': row[6] > 0
            })
        return sentences
    
    # ========== WORD DEFINITIONS ==========
    
    def add_word_definition(self, 
                           imported_content_id: int,
                           definition: str,
                           definition_language: str = 'native',
                           examples: Optional[List[str]] = None,
                           notes: str = '') -> int:
        """
        Add or update a word definition.
        
        Args:
            imported_content_id: ID of the imported word
            definition: The definition text
            definition_language: 'native' or language code
            examples: List of example sentences
            notes: User's notes about the word
            
        Returns:
            The word_definitions ID
        """
        cursor = self.db.conn.cursor()
        
        # Get the word from imported_content
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"No imported content found with ID {imported_content_id}")
        
        word = result[0]
        now = datetime.now().isoformat()
        examples_json = json.dumps(examples or [])
        
        # Check if definition already exists for this language
        cursor.execute(
            "SELECT id FROM word_definitions WHERE imported_content_id = ? AND definition_language = ?",
            (imported_content_id, definition_language)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE word_definitions 
                SET definition = ?, last_updated = ?, examples = ?, notes = ?
                WHERE id = ?
            """, (definition, now, examples_json, notes, existing[0]))
            definition_id = existing[0]
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO word_definitions 
                (imported_content_id, word, definition, definition_language, created_at, last_updated, examples, notes, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (imported_content_id, word, definition, definition_language, now, now, examples_json, notes, 'user'))
            definition_id = cursor.lastrowid
        
        self.db.conn.commit()
        return definition_id
    
    def get_word_definition(self, imported_content_id: int, 
                           language: Optional[str] = None) -> Optional[Dict]:
        """
        Get the word definition in the specified language.
        
        Args:
            imported_content_id: ID of the imported word
            language: 'native' or language code (uses preference if None)
            
        Returns:
            Dictionary with definition data or None
        """
        if language is None:
            language = 'native' if self.prefer_native_definitions else self.study_language
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, word, definition, definition_language, created_at, last_updated, 
                   examples, notes, difficulty_level, source
            FROM word_definitions
            WHERE imported_content_id = ? AND definition_language = ?
        """, (imported_content_id, language))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'word': row[1],
            'definition': row[2],
            'language': row[3],
            'created_at': row[4],
            'last_updated': row[5],
            'examples': json.loads(row[6]) if row[6] else [],
            'notes': row[7],
            'difficulty_level': row[8],
            'source': row[9]
        }
    
    def get_all_word_definitions(self, imported_content_id: int) -> List[Dict]:
        """Get all definitions for a word in all languages."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, word, definition, definition_language, created_at, last_updated,
                   examples, notes, difficulty_level, source
            FROM word_definitions
            WHERE imported_content_id = ?
            ORDER BY definition_language
        """, (imported_content_id,))
        
        definitions = []
        for row in cursor.fetchall():
            definitions.append({
                'id': row[0],
                'word': row[1],
                'definition': row[2],
                'language': row[3],
                'created_at': row[4],
                'last_updated': row[5],
                'examples': json.loads(row[6]) if row[6] else [],
                'notes': row[7],
                'difficulty_level': row[8],
                'source': row[9]
            })
        return definitions
    
    def generate_word_definition(self, imported_content_id: int, 
                                language: str = 'native',
                                use_simplified: bool = True) -> Tuple[bool, str]:
        """
        Generate a word definition using Ollama.
        
        Args:
            imported_content_id: ID of the imported word
            language: 'native' or language code
            use_simplified: Use simplified phrases for study language
            
        Returns:
            Tuple of (success: bool, definition: str)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available"
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            return False, "Word not found"
        
        word = result[0]
        
        # Build prompt
        if language == 'native':
            target_lang = self.native_language
            prompt = f"""Provide a clear, concise definition of the word "{word}" in {self.native_language}.
Keep it to 1-2 sentences. Include context about common usage."""
        else:
            target_lang = language or self.study_language
            if use_simplified:
                prompt = f"""Explain the word "{word}" in {self.study_language} using simple, common words that a beginner would understand.
Use present tense and active voice. Keep it to 1-2 sentences."""
            else:
                prompt = f"""Provide a definition of the word "{word}" in {self.study_language}."""
        
        # Generate using Ollama
        try:
            definition = self.ollama_client.generate_response(prompt)
            if definition:
                # Store the generated definition
                self.add_word_definition(
                    imported_content_id,
                    definition,
                    language,
                    notes=f"Generated by {self.ollama_client.model}"
                )
                return True, definition
            else:
                return False, "Failed to generate definition"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def set_word_difficulty(self, word_definition_id: int, difficulty: int):
        """Set difficulty level (0-5) for a word definition."""
        difficulty = max(0, min(5, difficulty))  # Clamp to 0-5
        cursor = self.db.conn.cursor()
        cursor.execute(
            "UPDATE word_definitions SET difficulty_level = ? WHERE id = ?",
            (difficulty, word_definition_id)
        )
        self.db.conn.commit()
    
    # ========== SENTENCE EXPLANATIONS ==========
    
    def add_sentence_explanation(self,
                                imported_content_id: int,
                                explanation: str,
                                explanation_language: str = 'native',
                                focus_area: str = 'all',
                                grammar_notes: str = '',
                                user_notes: str = '') -> int:
        """
        Add or update a sentence explanation.
        
        Args:
            imported_content_id: ID of the imported sentence
            explanation: The explanation text
            explanation_language: 'native' or language code
            focus_area: 'grammar', 'vocabulary', 'context', or 'all'
            grammar_notes: Specific grammar explanations
            user_notes: User's own notes
            
        Returns:
            The sentence_explanations ID
        """
        cursor = self.db.conn.cursor()
        
        # Get the sentence from imported_content
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"No imported content found with ID {imported_content_id}")
        
        sentence = result[0]
        now = datetime.now().isoformat()
        
        # Insert or update
        cursor.execute(
            "SELECT id FROM sentence_explanations WHERE imported_content_id = ? AND explanation_language = ?",
            (imported_content_id, explanation_language)
        )
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE sentence_explanations
                SET explanation = ?, focus_area = ?, grammar_notes = ?, 
                    user_notes = ?, last_updated = ?
                WHERE id = ?
            """, (explanation, focus_area, grammar_notes, user_notes, now, existing[0]))
            explanation_id = existing[0]
        else:
            cursor.execute("""
                INSERT INTO sentence_explanations
                (imported_content_id, sentence, explanation, explanation_language, 
                 focus_area, grammar_notes, user_notes, created_at, last_updated, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (imported_content_id, sentence, explanation, explanation_language,
                  focus_area, grammar_notes, user_notes, now, now, 'user'))
            explanation_id = cursor.lastrowid
        
        self.db.conn.commit()
        return explanation_id
    
    def get_sentence_explanation(self, imported_content_id: int,
                                language: Optional[str] = None) -> Optional[Dict]:
        """
        Get the sentence explanation in the specified language.
        
        Args:
            imported_content_id: ID of the imported sentence
            language: 'native' or language code (uses preference if None)
            
        Returns:
            Dictionary with explanation data or None
        """
        if language is None:
            language = 'native' if self.prefer_native_explanations else self.study_language
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, sentence, explanation, explanation_language, focus_area,
                   grammar_notes, user_notes, created_at, last_updated, source
            FROM sentence_explanations
            WHERE imported_content_id = ? AND explanation_language = ?
        """, (imported_content_id, language))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'sentence': row[1],
            'explanation': row[2],
            'language': row[3],
            'focus_area': row[4],
            'grammar_notes': row[5],
            'user_notes': row[6],
            'created_at': row[7],
            'last_updated': row[8],
            'source': row[9]
        }
    
    def get_all_sentence_explanations(self, imported_content_id: int) -> List[Dict]:
        """Get all explanations for a sentence in all languages."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, sentence, explanation, explanation_language, focus_area,
                   grammar_notes, user_notes, created_at, last_updated, source
            FROM sentence_explanations
            WHERE imported_content_id = ?
            ORDER BY explanation_language
        """, (imported_content_id,))
        
        explanations = []
        for row in cursor.fetchall():
            explanations.append({
                'id': row[0],
                'sentence': row[1],
                'explanation': row[2],
                'language': row[3],
                'focus_area': row[4],
                'grammar_notes': row[5],
                'user_notes': row[6],
                'created_at': row[7],
                'last_updated': row[8],
                'source': row[9]
            })
        return explanations
    
    def generate_sentence_explanation(self, imported_content_id: int,
                                     language: str = 'native',
                                     focus_area: str = 'all') -> Tuple[bool, str]:
        """
        Generate a sentence explanation using Ollama.
        
        Args:
            imported_content_id: ID of the imported sentence
            language: 'native' or language code
            focus_area: 'grammar', 'vocabulary', 'context', or 'all'
            
        Returns:
            Tuple of (success: bool, explanation: str)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available"
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            return False, "Sentence not found"
        
        sentence = result[0]
        
        # Build focus-specific prompt
        focus_prompts = {
            'grammar': f"""Explain the grammar structures in this sentence in {self.native_language if language == 'native' else self.study_language}:
"{sentence}"
Focus on tense, verb forms, and sentence structure.""",
            
            'vocabulary': f"""Explain the key vocabulary words in this sentence in {self.native_language if language == 'native' else self.study_language}:
"{sentence}"
Focus on word meanings and usage.""",
            
            'context': f"""Explain the context and meaning of this sentence in {self.native_language if language == 'native' else self.study_language}:
"{sentence}"
Focus on what the sentence means and when it would be used.""",
            
            'all': f"""Provide a comprehensive explanation of this sentence in {self.native_language if language == 'native' else self.study_language}:
"{sentence}"
Include grammar, vocabulary, and context. Keep it concise (3-4 sentences)."""
        }
        
        prompt = focus_prompts.get(focus_area, focus_prompts['all'])
        
        # Generate using Ollama
        try:
            explanation = self.ollama_client.generate_response(prompt)
            if explanation:
                # Store the generated explanation
                self.add_sentence_explanation(
                    imported_content_id,
                    explanation,
                    language,
                    focus_area,
                    user_notes=f"Generated by {self.ollama_client.model}"
                )
                return True, explanation
            else:
                return False, "Failed to generate explanation"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # ========== STUDY STATISTICS ==========
    
    def get_study_statistics(self) -> Dict:
        """Get overall study statistics."""
        cursor = self.db.conn.cursor()
        
        # Count words
        cursor.execute("SELECT COUNT(*) FROM imported_content WHERE content_type = 'word'")
        total_words = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT imported_content_id) 
            FROM word_definitions
        """)
        words_with_definitions = cursor.fetchone()[0]
        
        # Count sentences
        cursor.execute("SELECT COUNT(*) FROM imported_content WHERE content_type = 'sentence'")
        total_sentences = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT imported_content_id)
            FROM sentence_explanations
        """)
        sentences_with_explanations = cursor.fetchone()[0]
        
        return {
            'total_words': total_words,
            'words_with_definitions': words_with_definitions,
            'words_percentage': (words_with_definitions / total_words * 100) if total_words > 0 else 0,
            'total_sentences': total_sentences,
            'sentences_with_explanations': sentences_with_explanations,
            'sentences_percentage': (sentences_with_explanations / total_sentences * 100) if total_sentences > 0 else 0
        }
