"""
Vocabulary Extractor for Immersive Reading Mode.

Extracts vocabulary from reading sessions and creates flashcards for review.
Implements fair use compliance by limiting context to 200 characters.
"""

from typing import Dict, List, Optional
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager


class VocabExtractor:
    """
    Extracts vocabulary from reading sessions and creates flashcards.
    
    Implements fair use compliance by:
    - Extracting only individual words (not phrases)
    - Using minimal context (max 200 characters)
    - Preserving user's flashcards when reading sessions are deleted
    """
    
    # Maximum context length for fair use compliance (Requirement 8.3)
    MAX_CONTEXT_LENGTH = 200
    
    def __init__(self, study_manager: StudyManager, db: FlashcardDatabase):
        """
        Initialize the VocabExtractor.
        
        Args:
            study_manager: StudyManager instance for flashcard creation
            db: FlashcardDatabase instance for data access
        """
        self.study_manager = study_manager
        self.db = db
    
    def get_minimal_context(self, word: str, full_sentence: str) -> str:
        """
        Extract minimal context (max 200 chars) centered on the target word.
        
        This method ensures fair use compliance by limiting the context
        length while preserving the target word in the extracted snippet.
        
        Args:
            word: The target word to center the context on
            full_sentence: The complete sentence containing the word
            
        Returns:
            Truncated sentence centered on the word, max 200 characters
            
        Requirements: 8.3
        """
        # If the full sentence is already within the limit, return it
        if len(full_sentence) <= self.MAX_CONTEXT_LENGTH:
            return full_sentence
        
        # Find the position of the word in the sentence (case-insensitive)
        word_lower = word.lower()
        sentence_lower = full_sentence.lower()
        word_pos = sentence_lower.find(word_lower)
        
        if word_pos == -1:
            # Word not found, return first 200 characters
            return full_sentence[:self.MAX_CONTEXT_LENGTH]
        
        # Calculate start and end positions to center the word
        # We want the word to be roughly in the middle of the extracted text
        half_length = self.MAX_CONTEXT_LENGTH // 2
        
        start_pos = max(0, word_pos - half_length)
        end_pos = min(len(full_sentence), word_pos + half_length)
        
        # Adjust to avoid cutting in the middle of words if possible
        # Find word boundaries around the extracted range
        if start_pos > 0:
            # Find previous space
            prev_space = full_sentence.rfind(' ', 0, start_pos)
            if prev_space != -1:
                start_pos = prev_space + 1
        
        if end_pos < len(full_sentence):
            # Find next space
            next_space = full_sentence.find(' ', end_pos)
            if next_space != -1:
                end_pos = next_space
        
        # Extract the context
        context = full_sentence[start_pos:end_pos].strip()
        
        # Ensure we don't exceed the limit
        if len(context) > self.MAX_CONTEXT_LENGTH:
            context = context[:self.MAX_CONTEXT_LENGTH]
        
        return context
    
    def extract_word_from_lookup(self, lookup_id: int, session_id: int) -> int:
        """
        Extract word from lookup and create a flashcard.
        
        This method retrieves the lookup details, extracts minimal context,
        and creates a flashcard using StudyManager. It preserves the
        definition if one was generated during the lookup.
        
        Args:
            lookup_id: ID of the lookup record
            session_id: Reading session ID
            
        Returns:
            flashcard_id: ID of the created flashcard
            
        Requirements: 8.1, 8.2, 8.4, 8.5, 13.1
        """
        cursor = self.db.conn.cursor()
        
        # Get lookup details
        cursor.execute("""
            SELECT word, sentence_context, definition
            FROM reading_lookups
            WHERE id = ? AND session_id = ?
        """, (lookup_id, session_id))
        
        lookup = cursor.fetchone()
        
        if not lookup:
            raise ValueError(f"Lookup not found: {lookup_id}")
        
        word = lookup[0]
        sentence_context = lookup[1]
        definition = lookup[2]
        
        # Extract minimal context (max 200 chars)
        context = self.get_minimal_context(word, sentence_context)
        
        # Create imported_content entry for the word
        content_id = self.db.add_imported_content(
            content_type='word',
            content=word,
            context=context,
            url=f'reading_mode_session_{session_id}',
            language='en',  # Default to English
            title=f'Word from Reading Session'
        )
        
        # Add the word to StudyManager
        word_id = self.study_manager.add_manual_word(
            word=word,
            language='en',  # Default to English
            context=context,
            source_url=f'reading_mode_session_{session_id}',
            source_title=f'Word from Reading Session #{session_id}'
        )
        
        # If definition exists, add it to the flashcard
        if definition:
            self.study_manager.add_word_definition(
                imported_content_id=word_id,
                definition=definition,
                definition_language='native'
            )
        
        return word_id
    
    def get_session_vocabulary(self, session_id: int) -> List[Dict]:
        """
        Get all vocabulary extracted from a reading session.
        
        Returns a list of all words that have been extracted from lookups
        in this session, along with their definitions and contexts.
        
        Args:
            session_id: Reading session ID
            
        Returns:
            List of dictionaries with:
            {
                'word': str,
                'definition': Optional[str],
                'context': str,
                'flashcard_id': int
            }
            
        Requirements: 8.6
        """
        cursor = self.db.conn.cursor()
        
        # Get all lookups from this session that have been extracted
        cursor.execute("""
            SELECT DISTINCT word, sentence_context, definition
            FROM reading_lookups
            WHERE session_id = ? AND word IS NOT NULL
        """, (session_id,))
        
        lookups = cursor.fetchall()
        
        result = []
        for lookup in lookups:
            word = lookup[0]
            sentence_context = lookup[1]
            definition = lookup[2]
            
            # Extract minimal context
            context = self.get_minimal_context(word, sentence_context)
            
            result.append({
                'word': word,
                'definition': definition,
                'context': context,
                'flashcard_id': 0  # Will be populated if needed
            })
        
        return result
    
    def get_session_vocabulary_with_flashcards(self, session_id: int) -> List[Dict]:
        """
        Get vocabulary with flashcard IDs for extracted words.
        
        This method joins the reading_lookups table with imported_content
        to find the flashcard IDs for extracted words.
        
        Args:
            session_id: Reading session ID
            
        Returns:
            List of dictionaries with word, definition, context, and flashcard_id
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT rl.word, rl.sentence_context, rl.definition, ic.id as flashcard_id
            FROM reading_lookups rl
            LEFT JOIN imported_content ic ON rl.word = ic.content
            WHERE rl.session_id = ? AND rl.word IS NOT NULL
        """, (session_id,))
        
        lookups = cursor.fetchall()
        
        result = []
        for lookup in lookups:
            word = lookup[0]
            sentence_context = lookup[1]
            definition = lookup[2]
            flashcard_id = lookup[3] if lookup[3] else 0
            
            context = self.get_minimal_context(word, sentence_context)
            
            result.append({
                'word': word,
                'definition': definition,
                'context': context,
                'flashcard_id': flashcard_id
            })
        
        return result
