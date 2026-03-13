"""Reading Assistant for AI-powered reading assistance.

This module provides the ReadingAssistant class which integrates with
StudyManager to provide contextual word definitions and sentence explanations
during reading sessions.
"""

from typing import Dict, Optional
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager
from src.features.reader.definition_cache import DefinitionCache


class ReadingAssistant:
    """Provides AI-powered reading assistance.
    
    The ReadingAssistant integrates with the existing StudyManager to leverage
    proven AI-powered definition and explanation generation. It uses
    DefinitionCache for performance optimization to minimize LLM calls.
    
    Requirements:
        - 13.3: Use StudyManager.generate_word_definition for definitions
        - 13.4: Use StudyManager.generate_sentence_explanation for explanations
        - 13.5: Use existing LLM_Service configuration
    """
    
    def __init__(self, study_manager: StudyManager, db: FlashcardDatabase):
        """Initialize the Reading Assistant.
        
        Args:
            study_manager: StudyManager instance for AI-powered features
            db: FlashcardDatabase instance for storage
        """
        self.study_manager = study_manager
        self.db = db
        self.cache = DefinitionCache(db)
    
    def get_word_definition(
        self,
        word: str,
        sentence_context: str,
        paragraph_context: str,
        language: str
    ) -> Dict:
        """Get contextual definition for a word.

        This method first checks the definition cache for performance. If a
        cached definition exists, it returns immediately. Otherwise, it creates
        a temporary imported_content entry and uses StudyManager to generate
        a new definition, which is then cached for future use.

        Args:
            word: The word to define
            sentence_context: Sentence containing the word
            paragraph_context: Surrounding paragraph for additional context
            language: Target language code

        Returns:
            Dictionary with definition data:
            {
                'word': str,
                'definition': str,
                'synonym': Optional[str],
                'example': str,
                'source': str  # 'cache' or 'generated'
            }

        Requirements:
            - 4.1: Display contextual definition popup
            - 4.2: Generate definition using surrounding context
            - 4.3: Include simplified synonym when available
            - 4.4: Provide example sentence
            - 13.3: Use StudyManager.generate_word_content method
        """
        # Check cache first for performance (Requirement 6.2)
        cached = self.cache.get_definition(word, language, sentence_context)
        if cached:
            return cached

        # Cache miss - generate new definition using StudyManager
        # Create temporary imported_content entry
        content_id = self.db.add_imported_content(
            content_type='word',
            content=word,
            context=sentence_context,
            url='reading_mode',
            language=language,
            title='Reading Mode Lookup'
        )

        # Generate definition using StudyManager (Requirement 13.3)
        success, definition, suggestions = self.study_manager.generate_word_content(
            content_id,
            content_type='definition',
            language='native'
        )

        if success:
            # Extract synonym and example from suggestions if available
            synonym = suggestions.get('synonym', None)
            example = suggestions.get('example', definition)  # Use definition as fallback

            # Store result in cache (Requirement 6.1)
            self.cache.store_definition(
                word=word,
                language=language,
                context=sentence_context,
                definition=definition,
                synonym=synonym,
                example=example
            )

            return {
                'word': word,
                'definition': definition,
                'synonym': synonym,
                'example': example,
                'source': 'generated'
            }
        else:
            # Return error information if generation failed
            return {
                'word': word,
                'definition': definition,  # Contains error message
                'synonym': None,
                'example': '',
                'source': 'error'
            }
    
    def get_sentence_explanation(
        self,
        sentence: str,
        paragraph_context: str,
        language: str,
        native_language: str
    ) -> Dict:
        """Get detailed sentence explanation.
        
        This method creates a temporary imported_content entry and uses
        StudyManager to generate a comprehensive sentence explanation including
        translation, grammar analysis, and cultural notes.
        
        Args:
            sentence: The sentence to explain
            paragraph_context: Surrounding paragraph for additional context
            language: Target language code
            native_language: User's native language for translation
            
        Returns:
            Dictionary with explanation data:
            {
                'sentence': str,
                'translation': str,
                'grammar_notes': List[str],
                'cultural_notes': Optional[str],
                'difficulty': str  # 'beginner', 'intermediate', 'advanced'
            }
            
        Requirements:
            - 5.1: Display sentence explanation panel
            - 5.2: Provide literal translation to native language
            - 5.3: Identify and explain key grammar structures
            - 5.4: Provide cultural or idiomatic notes when relevant
            - 5.5: Indicate difficulty level of the sentence
            - 13.4: Use StudyManager.generate_sentence_explanation method
        """
        # Create temporary imported_content entry
        content_id = self.db.add_imported_content(
            content_type='sentence',
            content=sentence,
            context=paragraph_context,
            url='reading_mode',
            language=language,
            title='Reading Mode Sentence Lookup'
        )
        
        # Generate explanation using StudyManager (Requirement 13.4)
        # Request comprehensive explanation with all focus areas
        success, explanation, suggestions = self.study_manager.generate_sentence_explanation(
            content_id,
            language='native',
            focus_areas=['all']  # Get comprehensive explanation
        )
        
        if success:
            # Parse the explanation to extract components
            # The explanation from StudyManager is formatted with sections
            grammar_notes = []
            cultural_notes = None
            translation = ""
            difficulty = "intermediate"  # Default
            
            # Extract grammar suggestions if available
            if 'grammar' in suggestions and suggestions['grammar']:
                grammar_notes = suggestions['grammar']
            
            # Parse explanation text for translation and cultural notes
            # The explanation typically contains sections marked with **headers**
            lines = explanation.split('\n')
            current_section = None
            
            for line in lines:
                line_stripped = line.strip()
                
                # Detect section headers
                if line_stripped.startswith('**') and line_stripped.endswith(':**'):
                    current_section = line_stripped.lower()
                    continue
                
                # Extract translation (usually in the first section or marked)
                if 'translation' in str(current_section) or (not translation and line_stripped and current_section):
                    if line_stripped and not line_stripped.startswith('**'):
                        translation = line_stripped
                
                # Extract cultural notes
                if 'cultural' in str(current_section) or 'idiomatic' in str(current_section):
                    if line_stripped and not line_stripped.startswith('**'):
                        cultural_notes = line_stripped
                
                # Extract grammar notes from explanation text
                if 'grammar' in str(current_section):
                    if line_stripped and not line_stripped.startswith('**') and line_stripped not in grammar_notes:
                        grammar_notes.append(line_stripped)
            
            # If no translation was extracted, use the first meaningful line
            if not translation and lines:
                for line in lines:
                    if line.strip() and not line.strip().startswith('**'):
                        translation = line.strip()
                        break
            
            # Estimate difficulty based on sentence length and complexity
            word_count = len(sentence.split())
            if word_count < 8:
                difficulty = "beginner"
            elif word_count < 15:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"
            
            return {
                'sentence': sentence,
                'translation': translation or explanation[:200],  # Fallback to first 200 chars
                'grammar_notes': grammar_notes,
                'cultural_notes': cultural_notes,
                'difficulty': difficulty
            }
        else:
            # Return error information if generation failed
            return {
                'sentence': sentence,
                'translation': explanation,  # Contains error message
                'grammar_notes': [],
                'cultural_notes': None,
                'difficulty': 'unknown'
            }
    
    def pre_generate_definitions(
        self,
        session_id: int,
        content: str,
        language: str
    ) -> None:
        """Background task to pre-generate definitions for common words.
        
        This method extracts unique words from the content, limits to the 500
        most frequent words, and generates definitions for each word to populate
        the cache. A small delay is added between generations to avoid
        overwhelming the LLM service.
        
        Args:
            session_id: Reading session ID (for logging/tracking)
            content: Full text content to extract words from
            language: Target language code
            
        Requirements:
            - 6.6: Pre-generate definitions for all words in newly imported content
        """
        import time
        import re
        from collections import Counter
        
        # Extract unique words from content
        # Use regex to find word boundaries, similar to DifficultyCalculator
        words = re.findall(r"\b[\w']+\b", content, re.UNICODE)
        words = [w for w in words if w.strip()]
        
        # Convert to lowercase for uniqueness check
        word_list = [w.lower() for w in words]
        
        # Count word frequencies
        word_freq = Counter(word_list)
        
        # Get the 500 most frequent words
        most_common = word_freq.most_common(500)
        words_to_generate = [word for word, count in most_common]
        
        # Generate definitions for each word
        for word in words_to_generate:
            # Find first occurrence of word in content for context
            sentence_context = self._find_sentence_with_word(word, content)
            
            # Check if definition already exists in cache
            cached = self.cache.get_definition(word, language, sentence_context)
            if cached:
                # Already cached, skip generation
                continue
            
            # Generate and cache definition
            try:
                definition = self.get_word_definition(
                    word=word,
                    sentence_context=sentence_context,
                    paragraph_context='',
                    language=language
                )
                
                # Small delay to avoid overwhelming LLM service (0.1 seconds)
                time.sleep(0.1)
                
            except Exception as e:
                # Log error but continue with other words
                print(f"Error generating definition for '{word}': {e}")
                continue
    
    def _find_sentence_with_word(self, word: str, content: str) -> str:
        """Find the first sentence containing the given word.
        
        Args:
            word: Word to search for (case-insensitive)
            content: Full text content
            
        Returns:
            First sentence containing the word, or empty string if not found
        """
        import re
        
        # Simple sentence splitting on common sentence endings
        sentences = re.split(r'[.!?。！？]+', content)
        
        # Search for word in sentences (case-insensitive)
        word_lower = word.lower()
        for sentence in sentences:
            if sentence.strip():
                # Check if word appears in sentence
                sentence_words = re.findall(r"\b[\w']+\b", sentence, re.UNICODE)
                sentence_words_lower = [w.lower() for w in sentence_words]
                
                if word_lower in sentence_words_lower:
                    return sentence.strip()
        
        # If not found, return empty string
        return ""


    def pre_generate_definitions(
        self,
        session_id: int,
        content: str,
        language: str
    ) -> None:
        """Background task to pre-generate definitions for common words.

        This method extracts unique words from the content, limits to the 500
        most frequent words, and generates definitions for each word to populate
        the cache. A small delay is added between generations to avoid
        overwhelming the LLM service.

        Args:
            session_id: Reading session ID (for logging/tracking)
            content: Full text content to extract words from
            language: Target language code

        Requirements:
            - 6.6: Pre-generate definitions for all words in newly imported content
        """
        import time
        import re
        from collections import Counter

        # Extract unique words from content
        # Use regex to find word boundaries, similar to DifficultyCalculator
        words = re.findall(r"\b[\w']+\b", content, re.UNICODE)
        words = [w for w in words if w.strip()]

        # Convert to lowercase for uniqueness check
        word_list = [w.lower() for w in words]

        # Count word frequencies
        word_freq = Counter(word_list)

        # Get the 500 most frequent words
        most_common = word_freq.most_common(500)
        words_to_generate = [word for word, count in most_common]

        # Generate definitions for each word
        for word in words_to_generate:
            # Find first occurrence of word in content for context
            sentence_context = self._find_sentence_with_word(word, content)

            # Check if definition already exists in cache
            cached = self.cache.get_definition(word, language, sentence_context)
            if cached:
                # Already cached, skip generation
                continue

            # Generate and cache definition
            try:
                definition = self.get_word_definition(
                    word=word,
                    sentence_context=sentence_context,
                    paragraph_context='',
                    language=language
                )

                # Small delay to avoid overwhelming LLM service (0.1 seconds)
                time.sleep(0.1)

            except Exception as e:
                # Log error but continue with other words
                print(f"Error generating definition for '{word}': {e}")
                continue

    def _find_sentence_with_word(self, word: str, content: str) -> str:
        """Find the first sentence containing the given word.

        Args:
            word: Word to search for (case-insensitive)
            content: Full text content

        Returns:
            First sentence containing the word, or empty string if not found
        """
        import re

        # Simple sentence splitting on common sentence endings
        sentences = re.split(r'[.!?。！？]+', content)

        # Search for word in sentences (case-insensitive)
        word_lower = word.lower()
        for sentence in sentences:
            if sentence.strip():
                # Check if word appears in sentence
                sentence_words = re.findall(r"\b[\w']+\b", sentence, re.UNICODE)
                sentence_words_lower = [w.lower() for w in sentence_words]

                if word_lower in sentence_words_lower:
                    return sentence.strip()

        # If not found, return empty string
        return ""


