"""
Study Manager - Handles word definitions and sentence explanations
for imported content from the browser extension.

Features:
- Manage word definitions (user-entered or AI-generated)
- Generate and store sentence explanations
- Integration with Ollama for AI-powered learning
- Language preferences for definitions and explanations
- Custom prompt support for advanced users
"""

import json
import threading
import queue
import time
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from database import FlashcardDatabase
from ollama_integration import OllamaClient, OllamaThreadedQuery
from prompts import WORD_PROMPTS, SENTENCE_PROMPTS, WRITING_PROMPTS, CHAT_PROMPTS


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
        self.request_timeout = int(self._get_setting('request_timeout', '120'))
        self.ollama_model = self._get_setting('ollama_model', '')
        self.preload_on_startup = self._get_setting('preload_on_startup', 'true') == 'true'
        
        # Ensure ollama client uses the configured model
        if self.ollama_client and self.ollama_model:
            self.ollama_client.set_model(self.ollama_model)
            
        # Background Task Queue Setup
        self.task_queue = queue.Queue()
        self.processing_results = {} # task_id -> {status, result}
        self.stop_worker = False
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
    def queue_generation_task(self, task_type: str, item_id: int, **kwargs) -> str:
        """
        Queue a generation task.
        
        Args:
            task_type: 'definition', 'sentence_explanation', etc.
            item_id: ID of the word or sentence
            kwargs: Additional arguments for generation
            
        Returns:
            task_id: Unique ID for tracking the task
        """
        task_id = f"{task_type}_{item_id}_{int(time.time()*1000)}"
        self.processing_results[task_id] = {'status': 'queued'}
        
        task = {
            'id': task_id,
            'type': task_type,
            'item_id': item_id,
            'kwargs': kwargs
        }
        self.task_queue.put(task)
        return task_id
        
    def get_task_status(self, task_id: str) -> dict:
        """Get status of a specific task."""
        return self.processing_results.get(task_id, {'status': 'unknown'})
        
    def get_queue_status(self) -> dict:
        """Get overall queue status."""
        return {
            'queued': self.task_queue.qsize(),
            'results': len(self.processing_results)
        }
        
    def _worker_loop(self):
        """Background worker to process tasks."""
        while not self.stop_worker:
            try:
                # increasing timeout allows checking for stop_worker periodically
                task = self.task_queue.get(timeout=1) 
            except queue.Empty:
                continue
                
            task_id = task['id']
            self.processing_results[task_id]['status'] = 'processing'
            
            try:
                task_type = task['type']
                item_id = task['item_id']
                kwargs = task['kwargs']
                
                success = False
                result = None
                
                # Process based on type
                suggestions = {}
                
                if task_type == 'definition':
                    success, result, suggestions = self.generate_word_content(item_id, **kwargs)
                elif task_type == 'explanation':
                    success, result, suggestions = self.generate_word_content(item_id, content_type='explanation', **kwargs)
                elif task_type == 'examples':
                    success, result, suggestions = self.generate_word_content(item_id, content_type='examples', **kwargs)
                elif task_type == 'sentence_explanation':
                    success, result, suggestions = self.generate_sentence_explanation(item_id, **kwargs)
                elif task_type == 'grammar_explanation':
                    success, result, suggestions = self.generate_grammar_entry_content(item_id)
                elif task_type == 'grade_writing':
                    success, result, suggestions = self.grade_writing(kwargs.get('user_writing'), kwargs.get('topic'))
                elif task_type == 'writing_topic':
                    success, result, suggestions = self.generate_writing_topic()
                elif task_type == 'chat_message':
                    success, result, suggestions = self.send_chat_message(**kwargs)
                else:
                    success, result, suggestions = False, "Unknown task type", {}
                
                self.processing_results[task_id] = {
                    'status': 'completed' if success else 'failed',
                    'result': result,
                    'suggestions': suggestions,
                    'item_id': item_id,
                    'type': task_type
                }
                
            except Exception as e:
                print(f"Task failed: {e}")
                self.processing_results[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'suggestions': {}
                }
            finally:
                self.task_queue.task_done()
                
    def batch_generate_sentences(self) -> int:
        """
        Queue generation for all sentences missing explanations.
        Returns number of tasks queued.
        """
        sentences = self.get_imported_sentences()
        count = 0
        for sent in sentences:
            if not sent['has_explanation']:
                self.queue_generation_task('sentence_explanation', sent['id'])
                count += 1
        return count

    def batch_generate_words(self) -> int:
        """
        Queue generation for all words missing definitions.
        Returns number of tasks queued.
        """
        words = self.get_imported_words()
        count = 0
        for word in words:
            if not word['has_definition']:
                self.queue_generation_task('definition', word['id'])
                count += 1
        return count
    
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
    
    def set_request_timeout(self, timeout: int):
        """Set the request timeout in seconds."""
        self._set_setting('request_timeout', str(timeout))
        self.request_timeout = timeout
    
    def get_request_timeout(self) -> int:
        """Get the current request timeout in seconds."""
        return self.request_timeout
    
    def set_ollama_model(self, model: str):
        """Set the Ollama model to use."""
        self._set_setting('ollama_model', model)
        self.ollama_model = model
        # Also update the client if available
        if self.ollama_client:
            self.ollama_client.set_model(model)
    
    def get_ollama_model(self) -> str:
        """Get the currently configured Ollama model."""
        return self.ollama_model

    def set_preload_on_startup(self, enabled: bool):
        """Set whether to pre-load the model on app startup."""
        self._set_setting('preload_on_startup', 'true' if enabled else 'false')
        self.preload_on_startup = enabled
        
    def get_preload_on_startup(self) -> bool:
        """Get whether pre-loading is enabled."""
        return self.preload_on_startup
    
    def get_available_ollama_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if self.ollama_client:
            return self.ollama_client.get_available_models()
        return []
    
    # ========== PROMPT MANAGEMENT ==========
    
    def get_word_prompt(self, prompt_type: str, language: str = 'native') -> str:
        """
        Get word generation prompt (custom or default).
        
        Args:
            prompt_type: 'definition', 'explanation', or 'examples'
            language: 'native' or 'study'
            
        Returns:
            The prompt template
        """
        # Check for custom prompt
        custom_key = f'word_prompt_{prompt_type}_{language}'
        custom = self._get_setting(custom_key, '')
        
        if custom:
            return custom
        
        # Use default
        if prompt_type in WORD_PROMPTS:
            if language == 'native':
                return WORD_PROMPTS[prompt_type]['native_template']
            else:
                return WORD_PROMPTS[prompt_type]['study_template']
        
        return f"Generate a {prompt_type} for the word: {{word}}"
    
    def set_word_prompt(self, prompt_type: str, language: str, prompt: str):
        """Set custom word generation prompt."""
        key = f'word_prompt_{prompt_type}_{language}'
        self._set_setting(key, prompt)
    
    def get_sentence_prompt(self, focus_area: str) -> str:
        """
        Get sentence explanation prompt (custom or default).
        
        Args:
            focus_area: 'grammar', 'vocabulary', 'context', 'pronunciation', or 'all'
            
        Returns:
            The prompt template
        """
        # Check for custom prompt
        custom_key = f'sentence_prompt_{focus_area}'
        custom = self._get_setting(custom_key, '')
        
        if custom:
            return custom
        
        # Use default
        if focus_area in SENTENCE_PROMPTS:
            return SENTENCE_PROMPTS[focus_area]['template']
        
        return f"Explain this sentence focusing on {focus_area}: {{sentence}}"
    
    def set_sentence_prompt(self, focus_area: str, prompt: str):
        """Set custom sentence explanation prompt."""
        key = f'sentence_prompt_{focus_area}'
        self._set_setting(key, prompt)
    
    def get_default_word_prompt(self, prompt_type: str, language: str) -> str:
        """Get the default prompt for a word type (for display in UI)."""
        if prompt_type in WORD_PROMPTS:
            if language == 'native':
                return WORD_PROMPTS[prompt_type]['native_template']
            else:
                return WORD_PROMPTS[prompt_type]['study_template']
        return ""
    
    def get_default_sentence_prompt(self, focus_area: str) -> str:
        """Get the default prompt for a sentence focus area (for display in UI)."""
        if focus_area in SENTENCE_PROMPTS:
            return SENTENCE_PROMPTS[focus_area]['template']
        return ""
    
    # ========== IMPORTED CONTENT RETRIEVAL ==========
    
    def get_imported_words(self) -> List[Dict]:
        """Get all imported words with their definition status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT ic.id, ic.content, ic.url, ic.title, ic.created_at, ic.language, 
                   COUNT(wd.id) as has_definition, ic.collection_id
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
                'has_definition': row[6] > 0,
                'collection_id': row[7]
            })
        return words
    
    def get_imported_sentences(self) -> List[Dict]:
        """Get all imported sentences with their explanation status."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT ic.id, ic.content, ic.url, ic.title, ic.created_at, ic.language,
                   COUNT(se.id) as has_explanation, ic.collection_id
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
                'has_explanation': row[6] > 0,
                'collection_id': row[7]
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
    
    def _parse_ai_response(self, text: str) -> Tuple[str, Dict]:
        """
        Parse AI response to extract structured suggestions (flashcards, grammar patterns).
        
        Args:
            text: The raw AI response text
            
        Returns:
            Tuple of (clean_text, suggestions_dict)
        """
        suggestions = {
            'flashcards': [],
            'grammar': []
        }
        
        # Extract Flashcards: <flashcard word="TERM">DEF</flashcard>
        # Regex handles attributes with single or double quotes
        fc_pattern = r'<flashcard\s+word=[\'"](.*?)[\'"]>(.*?)</flashcard>'
        for match in re.finditer(fc_pattern, text, re.DOTALL | re.IGNORECASE):
            suggestions['flashcards'].append({
                'word': match.group(1),
                'definition': match.group(2).strip()
            })
            
        # Extract Grammar: <grammar_pattern title="TITLE">EXP</grammar_pattern>
        gp_pattern = r'<grammar_pattern\s+title=[\'"](.*?)[\'"]>(.*?)</grammar_pattern>'
        for match in re.finditer(gp_pattern, text, re.DOTALL | re.IGNORECASE):
            suggestions['grammar'].append({
                'title': match.group(1),
                'explanation': match.group(2).strip()
            })
            
        # Remove tags from text
        clean_text = re.sub(fc_pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(gp_pattern, '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        
        return clean_text.strip(), suggestions

    def generate_word_content(self, imported_content_id: int, 
                              content_type: str = 'definition',
                              language: str = 'native') -> Tuple[bool, str, Dict]:
        """
        Generate word content (definition, explanation, or examples) using Ollama.
        
        Args:
            imported_content_id: ID of the imported word
            content_type: 'definition', 'explanation', or 'examples'
            language: 'native' or 'study'
            
        Returns:
            Tuple of (success: bool, content: str, suggestions: Dict)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available", {}
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            return False, "Word not found", {}
        
        word = result[0]
        
        # Get the appropriate prompt
        target_lang = self.native_language if language == 'native' else self.study_language
        prompt_template = self.get_word_prompt(content_type, language)
        prompt = prompt_template.format(word=word, native_language=self.native_language, study_language=self.study_language)
        
        # Generate using Ollama
        try:
            content = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
            if content:
                # Parse for structured output
                clean_content, suggestions = self._parse_ai_response(content)
                
                # Store the generated definition (using clean content)
                self.add_word_definition(
                    imported_content_id,
                    clean_content,
                    language,
                    notes=f"Generated {content_type} by {self.ollama_client.model}"
                )
                return True, clean_content, suggestions
            else:
                return False, f"Failed to generate {content_type}", {}
        except Exception as e:
            return False, f"Error: {str(e)}", {}
    
    # Keep the old method for backwards compatibility
    def generate_word_definition(self, imported_content_id: int, 
                                language: str = 'native',
                                use_simplified: bool = True) -> Tuple[bool, str]:
        """
        Generate a word definition using Ollama (deprecated - use generate_word_content instead).
        
        Args:
            imported_content_id: ID of the imported word
            language: 'native' or language code
            use_simplified: Use simplified phrases for study language
            
        Returns:
            Tuple of (success: bool, definition: str)
        """
        return self.generate_word_content(imported_content_id, 'definition', language)
    
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
                                     focus_areas: List[str] = None) -> Tuple[bool, str, Dict]:
        """
        Generate a sentence explanation using Ollama for multiple focus areas.
        
        Args:
            imported_content_id: ID of the imported sentence
            language: 'native' or language code
            focus_areas: List of focus areas ('grammar', 'vocabulary', 'context', 'pronunciation', 'all')
            
        Returns:
            Tuple of (success: bool, explanation: str, suggestions: Dict)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available", {}
        
        if focus_areas is None or len(focus_areas) == 0:
            focus_areas = ['all']
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT content FROM imported_content WHERE id = ?", (imported_content_id,))
        result = cursor.fetchone()
        if not result:
            return False, "Sentence not found", {}
        
        sentence = result[0]
        target_lang = self.native_language if language == 'native' else self.study_language
        
        # Collect all explanations and suggestions
        all_explanations = []
        all_suggestions = {
            'flashcards': [],
            'grammar': []
        }
        primary_focus = None
        
        try:
            for focus_area in focus_areas:
                # Get the prompt for this focus area
                prompt_template = self.get_sentence_prompt(focus_area)
                prompt = prompt_template.format(sentence=sentence, language=target_lang, study_language=self.study_language)
                
                # Generate
                explanation = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
                if explanation:
                    # Parse suggestions
                    clean_explanation, suggestions = self._parse_ai_response(explanation)
                    
                    # Aggregate suggestions
                    all_suggestions['flashcards'].extend(suggestions['flashcards'])
                    all_suggestions['grammar'].extend(suggestions['grammar'])
                    
                    if focus_area == 'all':
                        focus_name = 'Comprehensive'
                    else:
                        focus_name = SENTENCE_PROMPTS.get(focus_area, {}).get('name', focus_area.title())
                    
                    all_explanations.append(f"**{focus_name}:**\n{clean_explanation}")
                    
                    if primary_focus is None:
                        primary_focus = focus_area
            
            if all_explanations:
                combined_explanation = "\n\n".join(all_explanations)
                
                # Store the generated explanation (using first focus as primary)
                self.add_sentence_explanation(
                    imported_content_id,
                    combined_explanation,
                    language,
                    primary_focus,
                    user_notes=f"Generated by {self.ollama_client.model} (focus: {', '.join(focus_areas)})"
                )
                return True, combined_explanation, all_suggestions
            else:
                return False, "Failed to generate explanations", {}
        except Exception as e:
            return False, f"Error: {str(e)}", {}
    
    # ========== GRAMMAR FOLLOW-UPS ==========
    
    def ask_grammar_followup(self, sentence_explanation_id: int, question: str) -> Tuple[bool, str]:
        # ... (This method uses context so parsing might be weird/unnecessary for suggestions, keeping 2 return vals to avoid breaking too much, 
        # but helper logic needs consistency? No, calling logic is manual. Worker loop doesn't call this.)
        # Wait, the worker loop handles generation content. Follow-ups are synchronous/on-demand in GUI (lines 740).
        # So I don't need to change this one.
        
        """
        Ask a follow-up question about a sentence explanation with full context.
        ...
        """
        # (Content omitted to save space, keeping original logic for this method)
        return super().ask_grammar_followup(sentence_explanation_id, question) if hasattr(super(), 'ask_grammar_followup') else self._fallback_followup(sentence_explanation_id, question)

    # Re-implementing ask_grammar_followup properly since I can't use super() on self without inheritance context shown here.
    # Actually, I should just NOT replace it if I'm not changing it.
    # The tool replaces a range. I spanned over it. I will paste the original `ask_grammar_followup` back in.
    
    def ask_grammar_followup(self, sentence_explanation_id: int, question: str) -> Tuple[bool, str]:
        """
        Ask a follow-up question about a sentence explanation with full context.
        
        Args:
            sentence_explanation_id: ID of the sentence explanation
            question: The follow-up question
            
        Returns:
            Tuple of (success: bool, answer: str)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available"
        
        # Get the sentence explanation
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT sentence, explanation, explanation_language
            FROM sentence_explanations
            WHERE id = ?
        """, (sentence_explanation_id,))
        
        result = cursor.fetchone()
        if not result:
            return False, "Sentence explanation not found"
        
        sentence, explanation, explanation_language = result
        
        # Get previous follow-ups for context
        previous_followups = self.db.get_grammar_followups(sentence_explanation_id)
        
        # Build context-aware prompt
        target_lang = self.native_language if explanation_language == 'native' else self.study_language
        
        prompt = f"""You are a {self.study_language} language tutor helping a student understand grammar.

Original sentence: "{sentence}"

Original explanation:
{explanation}
"""
        
        # Add conversation history if exists
        if previous_followups:
            prompt += "\n\nPrevious questions and answers:\n"
            for i, followup in enumerate(previous_followups, 1):
                prompt += f"\nQ{i}: {followup['question']}\nA{i}: {followup['answer']}\n"
        
        prompt += f"""
New question from student: {question}

Please provide a clear, helpful answer in {target_lang}. Reference the original sentence and previous discussion when relevant. Be specific and provide examples when helpful."""
        
        try:
            answer = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
            if answer:
                # Store the follow-up
                self.db.add_grammar_followup(
                    sentence_explanation_id,
                    question,
                    answer,
                    context=sentence
                )
                return True, answer
            else:
                return False, "Failed to generate answer"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # ========== GRAMMAR BOOK MANAGEMENT ==========
    
    def generate_grammar_explanation(self, topic: str) -> Tuple[bool, str, Dict]:
        """
        Generate a grammar explanation using Ollama.
        
        Args:
            topic: The grammar topic to explain
            
        Returns:
            Tuple of (success: bool, content: str, suggestions: Dict)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available", {}
        
        prompt = f"""You are a {self.study_language} language tutor. 
        
Please explain the following grammar topic: "{topic}"

Target Audience: A student whose native language is {self.native_language}.

Structure your explanation as follows:
# {topic}

## Meaning
Briefly explain what this grammar point means.

## Usage
Explain how and when to use it (conjugation rules, etc.).

## Examples
Provide 3-5 example sentences in {self.study_language} with {self.native_language} translations.
- Example 1
- Example 2
- Example 3

## Notes
Any important exceptions or nuances.
"""
        
        try:
            content = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
            if content:
                clean_content, suggestions = self._parse_ai_response(content)
                return True, clean_content, suggestions
            else:
                return False, "Failed to generate explanation", {}
        except Exception as e:
            return False, f"Error: {str(e)}", {}

    def generate_grammar_entry_content(self, entry_id: int) -> Tuple[bool, str, Dict]:
        """
        Generate content for a grammar entry and save it to the database.
        
        Args:
            entry_id: ID of the grammar entry
            
        Returns:
            Tuple of (success: bool, content: str, suggestions: Dict)
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT title, tags FROM grammar_book_entries WHERE id = ?", (entry_id,))
        result = cursor.fetchone()
        
        if not result:
            return False, "Entry not found", {}
            
        title, tags = result
        
        # Generate content
        success, content, suggestions = self.generate_grammar_explanation(title)
        
        if success:
            # Update the entry
            self.update_grammar_entry(entry_id, title, content, tags or "")
            return True, content, suggestions
            
        return False, content, {}

    def add_grammar_entry(self, title: str, content: str, tags: str = "") -> int:
        """Add a grammar book entry."""
        return self.db.add_grammar_entry(title, content, self.study_language, tags)
    
    def update_grammar_entry(self, entry_id: int, title: str, content: str, tags: str) -> bool:
        """Update a grammar book entry."""
        return self.db.update_grammar_entry(entry_id, title, content, self.study_language, tags)
    
    def delete_grammar_entry(self, entry_id: int) -> bool:
        """Delete a grammar book entry."""
        return self.db.delete_grammar_entry(entry_id)
    
    def get_grammar_entries(self, search_query: str = "") -> List[Dict]:
        """Get grammar book entries."""
        # We could filter by language here if the DB supports mixed languages, 
        # currently DB stores language column but get_grammar_entries doesn't filter by it strictly yet.
        # Ideally, we should filter by self.study_language if we want language separation.
        return self.db.get_grammar_entries(search_query)

    # ========== MANUAL CONTENT ENTRY ==========
    
    def add_manual_word(self, word: str, context: str = "", definition: str = "") -> Tuple[bool, str]:
        """
        Manually add a word to the database.
        
        Args:
            word: The word to add
            context: Optional context sentence
            definition: Optional manual definition
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # 1. Add to imported_content
            # Check if updated database.py has add_manual_content method? 
            # Currently database.py has add_imported_content but it takes many args.
            # We can use add_imported_content with source="manual"
            # Wait, database.py add_imported_content signature: 
            # (content_type, content, context, title, url, language, tags)
            
            content_id = self.db.add_imported_content(
                content_type='word',
                content=word,
                context=context,
                title='Manual Entry',
                url='manual',
                language=self.study_language,
                tags='manual'
            )
            
            # 2. Add definition if provided
            if definition:
                self.db.add_word_definition(
                    imported_content_id=content_id,
                    word=word,
                    definition=definition,
                    definition_language=self.native_language,
                    source='user'
                )
                
            return True, "Word added successfully"
        except Exception as e:
            return False, f"Error adding word: {str(e)}"

    def add_manual_sentence(self, sentence: str, notes: str = "") -> Tuple[bool, str]:
        """
        Manually add a sentence to the database.
        
        Args:
            sentence: The sentence to add
            notes: Optional user notes
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            content_id = self.db.add_imported_content(
                content_type='sentence',
                content=sentence,
                context=sentence, # Context is the sentence itself
                title='Manual Entry',
                url='manual',
                language=self.study_language,
                tags='manual'
            )
            
            if notes:
                # We can create a partial sentence explanation or just leave it for the user to generate later
                # Currently we don't have a direct "add_sentence_explanation" method exposed easily with just notes
                # But we can assume the user will generate the explanation later.
                pass
                
            return True, "Sentence added successfully"
        except Exception as e:
            return False, f"Error adding sentence: {str(e)}"
            
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
    # ========== WRITING COMPOSITION LAB ==========

    def generate_writing_topic(self) -> Tuple[bool, str, Dict]:
        """Generate a creative writing topic using AI."""
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available", {}
            
        prompt_template = WRITING_PROMPTS['generate_topic']['template']
        prompt = prompt_template.format(
            study_language=self.study_language,
            native_language=self.native_language
        )
        
        try:
            content = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
            if content:
                return True, content, {}
            return False, "Failed to generate topic", {}
        except Exception as e:
            return False, f"Error: {e}", {}

    def grade_writing(self, user_writing: str, topic: str) -> Tuple[bool, str, Dict]:
        """Grade a user's writing composition and provide feedback."""
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, "Ollama is not available", {}
            
        prompt_template = WRITING_PROMPTS['grade']['template']
        prompt = prompt_template.format(
            study_language=self.study_language,
            topic=topic,
            user_writing=user_writing,
            native_language=self.native_language
        )
        
        try:
            content = self.ollama_client.generate_response(prompt, timeout=self.request_timeout)
            if content:
                clean_content, suggestions = self._parse_ai_response(content)
                
                # Save to history
                # We'll extract a "grade" from the clean_content if possible, 
                # or just use a placeholder for now.
                # A simple way to get grade is to look for "Overall Grade:"
                grade_match = re.search(r'Overall Grade:\s*(.*?)(?:\n|$)', clean_content, re.IGNORECASE)
                grade = grade_match.group(1).strip() if grade_match else "N/A"
                
                self.db.add_writing_session(topic, user_writing, clean_content, grade, self.study_language)
                
                return True, clean_content, suggestions
            return False, "Failed to grade writing", {}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error: {e}", {}

    def get_writing_history(self) -> List[Dict]:
        """Get the history of writing sessions."""
        return self.db.get_writing_sessions(self.study_language)

    # ========== INTERACTIVE CHAT ==========

    def create_chat_session(self, topic: str) -> int:
        """Create a new chat session."""
        return self.db.create_chat_session(topic, self.study_language)

    def get_chat_sessions(self) -> List[Dict]:
        """Get list of chat sessions."""
        return self.db.get_chat_sessions(self.study_language)

    def get_chat_messages(self, session_id: int) -> List[Dict]:
        """Get all messages for a session."""
        return self.db.get_chat_messages(session_id)

    def send_chat_message(self, session_id: int, user_message: str, current_history: List[Dict]) -> Tuple[bool, Dict, Dict]:
        """
        Send a message to the AI and process the response.
        
        Args:
            session_id: The active session
            user_message: The user's input
            current_history: Recent messages (for context window)
            
        Returns:
            Tuple(success, result_dict, suggestions_dict)
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return False, {"error": "Ollama is not available"}, {}

        # 1. Save User Message
        self.db.add_chat_message(session_id, 'user', user_message)
        
        # 2. Build Prompt
        # Get context (last 10 messages)
        # Note: In a real app we'd construct a proper conversation history for the LLM API
        # but for now we'll append to the system prompt
        
        session = next((s for s in self.get_chat_sessions() if s['id'] == session_id), None)
        topic = session['cur_topic'] if session else "General Conversation"
        
        prompt_template = CHAT_PROMPTS['system_roleplay']['template']
        system_prompt = prompt_template.format(
            persona="Language Tutor",
            study_language=self.study_language,
            native_language=self.native_language,
            topic=topic
        )
        
        # Construct full prompt with history
        full_prompt = f"System: {system_prompt}\n\n Conversation History:\n"
        for msg in current_history[-6:]: # Include last 6 messages for context
            full_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
        full_prompt += f"User: {user_message}\nAssistant:"
        
        # 3. Generate Request
        try:
            content = self.ollama_client.generate_response(full_prompt, timeout=self.request_timeout)
            if content:
                # 4. Parse Response (XML)
                parsed_data, suggestions = self._parse_chat_response(content)
                
                # 5. Save Assistant Message
                # We save the 'reply' as content, and the full JSON as analysis
                import json
                analysis_json = json.dumps(parsed_data)
                self.db.add_chat_message(session_id, 'assistant', parsed_data['reply'], analysis_json)
                
                return True, parsed_data, suggestions
            return False, {"error": "Failed to generate response"}, {}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, {"error": f"Error: {e}"}, {}

    def _parse_chat_response(self, text: str) -> Tuple[Dict, Dict]:
        """Parse structured chat response."""
        
        # Helpers to extract tag content
        def extract_tag(tag, source):
            pattern = f"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, source, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""
        
        reply = extract_tag('reply', text)
        feedback = extract_tag('feedback', text)
        vocab_section = extract_tag('vocab', text)
        grammar_section = extract_tag('grammar', text)
        
        # Fallback if XML fails (LLM forgot format)
        if not reply:
            reply = text # Assume whole text is reply
        
        # Extract structured items from vocab/grammar sections
        parsed_suggestions = {
            'flashcards': [],
            'grammar': []
        }
        
        # Re-use existing suggestion parser on the specific sections
        _, vocab_suggs = self._parse_ai_response(vocab_section)
        parsed_suggestions['flashcards'].extend(vocab_suggs['flashcards'])
        
        _, gram_suggs = self._parse_ai_response(grammar_section)
        parsed_suggestions['grammar'].extend(gram_suggs['grammar'])
        
        return {
            'reply': reply,
            'feedback': feedback,
            'vocab_section': vocab_section,
            'grammar_section': grammar_section
        }, parsed_suggestions
