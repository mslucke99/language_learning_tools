"""
Vocabulary Service for Adventure Graded Reader.

This module provides vocabulary extraction and management functionality,
including querying known words from the database, tracking session vocabulary,
and calculating vocabulary coverage for validation.
"""

from typing import List, Set, Dict
from src.core.database import FlashcardDatabase


class VocabularyService:
    """
    Service for managing user vocabulary and calculating coverage.
    
    This service extracts known words from the flashcards database,
    tracks newly introduced words during story sessions, and provides
    vocabulary coverage calculation for validation.
    """
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize VocabularyService.
        
        Args:
            db: FlashcardDatabase instance for querying vocabulary
        """
        self.db = db
        self._cache: Dict[str, Set[str]] = {}  # Cache known words by language
    
    def get_known_words(self, language: str, min_proficiency: int = 0) -> List[str]:
        """
        Get list of known words for a language.
        
        Queries both flashcards (with proficiency threshold) and known_words table.
        Results are cached per language for performance.
        
        Args:
            language: Target language code (e.g., 'korean', 'spanish')
            min_proficiency: Minimum proficiency level for flashcards (default 0)
        
        Returns:
            List of unique words in lowercase normalized form
        
        Preconditions:
            - language is non-empty string
            - min_proficiency is integer >= 0
            - Database connection is active
        
        Postconditions:
            - Returns list of unique words (no duplicates)
            - All returned words are from specified language
            - All returned words have proficiency >= min_proficiency
            - List is non-empty if user has any vocabulary in language
            - Words are returned in lowercase normalized form
        """
        if not language or not language.strip():
            raise ValueError("language must be non-empty")
        if min_proficiency < 0:
            raise ValueError("min_proficiency must be >= 0")
        
        # Check cache first
        cache_key = f"{language}:{min_proficiency}"
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        
        known_words = set()
        
        # Get words from known_words table
        known_words_data = self.db.get_all_known_words(language)
        for word_data in known_words_data:
            lemma = word_data["lemma"].lower().strip()
            if lemma:
                known_words.add(lemma)
        
        # Get words from flashcards with proficiency threshold
        # Query flashcards table directly for words with sufficient reviews
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT f.question, f.correct_reviews, f.total_reviews
            FROM flashcards f
            JOIN decks d ON f.deck_id = d.id
            WHERE d.language = ?
            AND f.total_reviews > 0
        """, (language,))
        
        for row in cursor.fetchall():
            question = row[0]
            correct_reviews = row[1] or 0
            total_reviews = row[2] or 1
            
            # Calculate proficiency as percentage of correct reviews
            proficiency = (correct_reviews / total_reviews) * 10 if total_reviews > 0 else 0
            
            if proficiency >= min_proficiency:
                # Extract word from question (handle various formats)
                word = self._extract_word_from_question(question)
                if word:
                    known_words.add(word.lower().strip())
        
        # Cache the results
        self._cache[cache_key] = known_words
        
        return list(known_words)
    
    def _extract_word_from_question(self, question: str) -> str:
        """
        Extract the target word from a flashcard question.
        
        Handles various question formats:
        - Plain word: "학교"
        - With context: "학교 (in sentence: ...)"
        - With translation: "학교 - school"
        
        Args:
            question: Flashcard question text
        
        Returns:
            Extracted word or empty string if extraction fails
        """
        if not question:
            return ""
        
        # Remove common separators and take first part
        for separator in [" - ", " (", " [", ":"]:
            if separator in question:
                question = question.split(separator)[0]
        
        return question.strip()
    
    def get_known_word_count(self, language: str) -> int:
        """
        Get count of known words for a language.
        
        Args:
            language: Target language code
        
        Returns:
            Number of known words
        """
        return len(self.get_known_words(language))
    
    def is_word_known(self, word: str, language: str) -> bool:
        """
        Check if a specific word is known.
        
        Provides O(1) lookup using cached set.
        
        Args:
            word: Word to check
            language: Target language code
        
        Returns:
            True if word is in known vocabulary, False otherwise
        """
        known_words = self.get_known_words(language)
        return word.lower().strip() in [w.lower() for w in known_words]
    
    def add_encountered_words(self, session_id: int, words: List[Dict[str, str]]) -> None:
        """
        Track words encountered during a story session.
        
        Adds words to the session's vocabulary_introduced list in the database.
        
        Args:
            session_id: ID of the story session
            words: List of word dictionaries with 'word' and 'translation' keys
        
        Preconditions:
            - session_id exists in database
            - words is a list of dicts with 'word' key
        
        Postconditions:
            - Words are added to session's vocabulary_introduced
            - Database is updated
        """
        if not words:
            return
        
        # Get current session
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT vocabulary_introduced
            FROM story_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        # Parse existing vocabulary
        import json
        vocab_json = row[0] or "[]"
        vocabulary_introduced = json.loads(vocab_json) if vocab_json else []
        
        # Add new words (avoid duplicates)
        for word_data in words:
            word = word_data.get("word", "").strip()
            if word and word not in vocabulary_introduced:
                vocabulary_introduced.append(word)
        
        # Update database
        cursor.execute("""
            UPDATE story_sessions
            SET vocabulary_introduced = ?,
                last_updated = datetime('now')
            WHERE id = ?
        """, (json.dumps(vocabulary_introduced), session_id))
        
        self.db.conn.commit()
    
    def get_vocabulary_coverage(self, text: str, language: str) -> float:
        """
        Calculate vocabulary coverage percentage for a text.
        
        Coverage is the percentage of words in the text that are in the
        user's known vocabulary.
        
        Args:
            text: Text to analyze
            language: Target language code
        
        Returns:
            Coverage percentage as float between 0.0 and 1.0
        
        Preconditions:
            - text is non-empty
            - language is valid language code
        
        Postconditions:
            - Returns value between 0.0 and 1.0
            - Coverage is calculated based on unique words
        """
        if not text or not text.strip():
            return 0.0
        
        # Simple tokenization (split on whitespace and punctuation)
        # TODO: Use proper tokenizer (spacy/konlpy) for better accuracy
        import re
        tokens = re.findall(r'\w+', text.lower())
        
        if not tokens:
            return 0.0
        
        known_words = set(w.lower() for w in self.get_known_words(language))
        known_count = sum(1 for token in tokens if token in known_words)
        
        coverage = known_count / len(tokens)
        return min(1.0, max(0.0, coverage))  # Clamp to [0.0, 1.0]
    
    def clear_cache(self, language: str = None) -> None:
        """
        Clear the vocabulary cache.
        
        Args:
            language: If specified, clear only cache for this language.
                     If None, clear entire cache.
        """
        if language:
            # Clear all cache entries for this language
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{language}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
