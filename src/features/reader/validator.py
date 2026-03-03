"""
Validation system for Adventure Graded Reader.

This module provides vocabulary validation functions to ensure that
generated story passages meet the required vocabulary constraints
(95% known words, 1-2 new words).
"""

from typing import List, Set
import re

from .models import StoryPassage, VocabularyConstraints, ValidationResult, NewWord


class VocabularyValidator:
    """
    Validator for checking vocabulary constraints in story passages.
    
    This validator tokenizes text, calculates vocabulary coverage,
    and ensures that passages meet the required constraints.
    """
    
    def __init__(self, language: str = "korean"):
        """
        Initialize VocabularyValidator.
        
        Args:
            language: Target language for tokenization
        """
        self.language = language
        self._tokenizer = None
        self._lemmatizer = None
        
        # Try to load language-specific tokenizer
        self._init_tokenizer()
    
    def _init_tokenizer(self):
        """
        Initialize language-specific tokenizer.
        
        For now, uses simple regex tokenization.
        TODO: Integrate spacy or konlpy for better accuracy.
        """
        # Simple tokenization for now
        # In production, use:
        # - spacy for Spanish, Japanese, Chinese
        # - konlpy (Kiwi) for Korean
        pass
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Uses simple regex tokenization for now.
        TODO: Replace with proper NLP tokenizer (spacy/konlpy).
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of tokens (words)
        """
        if not text:
            return []
        
        # Simple tokenization: extract word characters
        # This works reasonably well for Korean, Spanish, etc.
        tokens = re.findall(r'\w+', text.lower())
        return tokens
    
    def lemmatize(self, word: str) -> str:
        """
        Lemmatize a word to its base form.
        
        For now, just returns lowercase word.
        TODO: Implement proper lemmatization with NLP library.
        
        Args:
            word: Word to lemmatize
        
        Returns:
            Lemmatized word
        """
        return word.lower().strip()
    
    def validate_vocabulary(
        self,
        passage: StoryPassage,
        constraints: VocabularyConstraints
    ) -> ValidationResult:
        """
        Validate that a passage meets vocabulary constraints.
        
        Checks:
        1. Vocabulary coverage >= min_coverage (default 95%)
        2. New words count is between 1 and max_new_words
        3. All declared new words are present in story_text
        
        Args:
            passage: StoryPassage to validate
            constraints: VocabularyConstraints to check against
        
        Returns:
            ValidationResult with is_valid, coverage, and unknown_words
        
        Preconditions:
            - passage.story_text is non-empty
            - constraints.known_words is non-empty set
            - Tokenizer is available for target language
        
        Postconditions:
            - Returns ValidationResult with is_valid boolean
            - is_valid is true if and only if:
              - Vocabulary coverage >= vocabulary.min_coverage (default 0.95)
              - New words count is between 1 and vocabulary.max_new_words
              - All declared new words are actually present in story_text
            - coverage field contains accurate percentage (0.0 to 1.0)
            - unknown_words list contains all words not in known vocabulary
        """
        if not passage.story_text or not passage.story_text.strip():
            return ValidationResult(
                is_valid=False,
                coverage=0.0,
                unknown_words=[],
                message="story_text is empty"
            )
        
        # Tokenize passage text
        tokens = self.tokenize(passage.story_text)
        
        if not tokens:
            return ValidationResult(
                is_valid=False,
                coverage=0.0,
                unknown_words=[],
                message="No tokens found in story_text"
            )
        
        total_tokens = len(tokens)
        
        # Combine known words and session words
        all_known = constraints.known_words | constraints.session_words
        all_known_lower = {w.lower() for w in all_known}
        
        # Count known vs unknown words
        known_count = 0
        unknown_words = []
        
        for token in tokens:
            lemma = self.lemmatize(token)
            
            if lemma in all_known_lower:
                known_count += 1
            else:
                if lemma not in unknown_words:
                    unknown_words.append(lemma)
        
        # Calculate coverage
        coverage = known_count / total_tokens if total_tokens > 0 else 0.0
        
        # Validate new words count
        new_words_count = len(passage.new_words)
        
        # Check if coverage meets minimum
        coverage_ok = coverage >= constraints.min_coverage
        
        # Check if new words count is within limits
        new_words_ok = 1 <= new_words_count <= constraints.max_new_words
        
        # Check that declared new words are in unknown words
        declared_words_ok = True
        for new_word in passage.new_words:
            word_lower = new_word.word.lower()
            if word_lower not in unknown_words:
                # Word might be in text but not detected as unknown
                # This is OK if it's actually in the text
                if word_lower not in passage.story_text.lower():
                    declared_words_ok = False
                    break
        
        is_valid = coverage_ok and new_words_ok and declared_words_ok
        
        # Build message
        messages = []
        if not coverage_ok:
            messages.append(f"Coverage {coverage:.2%} < {constraints.min_coverage:.2%}")
        if not new_words_ok:
            messages.append(f"New words count {new_words_count} not in range [1, {constraints.max_new_words}]")
        if not declared_words_ok:
            messages.append("Some declared new words not found in text")
        
        message = "; ".join(messages) if messages else "Validation passed"
        
        return ValidationResult(
            is_valid=is_valid,
            coverage=coverage,
            unknown_words=unknown_words,
            message=message
        )
    
    def calculate_coverage(
        self,
        text: str,
        known_words: Set[str],
        session_words: Set[str] = None
    ) -> float:
        """
        Calculate vocabulary coverage for a text.
        
        Args:
            text: Text to analyze
            known_words: Set of known words
            session_words: Optional set of session words
        
        Returns:
            Coverage as float between 0.0 and 1.0
        """
        if not text or not text.strip():
            return 0.0
        
        tokens = self.tokenize(text)
        if not tokens:
            return 0.0
        
        all_known = known_words
        if session_words:
            all_known = known_words | session_words
        
        all_known_lower = {w.lower() for w in all_known}
        
        known_count = sum(1 for token in tokens if self.lemmatize(token) in all_known_lower)
        
        coverage = known_count / len(tokens)
        return min(1.0, max(0.0, coverage))
    
    def extract_unknown_words(
        self,
        text: str,
        known_words: Set[str],
        session_words: Set[str] = None
    ) -> List[str]:
        """
        Extract unknown words from text.
        
        Args:
            text: Text to analyze
            known_words: Set of known words
            session_words: Optional set of session words
        
        Returns:
            List of unknown words (unique)
        """
        if not text:
            return []
        
        tokens = self.tokenize(text)
        
        all_known = known_words
        if session_words:
            all_known = known_words | session_words
        
        all_known_lower = {w.lower() for w in all_known}
        
        unknown = []
        for token in tokens:
            lemma = self.lemmatize(token)
            if lemma not in all_known_lower and lemma not in unknown:
                unknown.append(lemma)
        
        return unknown
    
    def validate_new_word_presence(
        self,
        passage: StoryPassage
    ) -> bool:
        """
        Validate that all new words are present in story text.
        
        Args:
            passage: StoryPassage to validate
        
        Returns:
            True if all new words are in story_text, False otherwise
        """
        story_lower = passage.story_text.lower()
        
        for new_word in passage.new_words:
            if new_word.word.lower() not in story_lower:
                return False
        
        return True
    
    def validate_context_sentences(
        self,
        passage: StoryPassage
    ) -> bool:
        """
        Validate that context sentences contain their words.
        
        Args:
            passage: StoryPassage to validate
        
        Returns:
            True if all context sentences contain their words, False otherwise
        """
        for new_word in passage.new_words:
            if new_word.word.lower() not in new_word.context_sentence.lower():
                return False
        
        return True


def validate_passage(
    passage: StoryPassage,
    constraints: VocabularyConstraints,
    language: str = "korean"
) -> ValidationResult:
    """
    Convenience function to validate a passage.
    
    Args:
        passage: StoryPassage to validate
        constraints: VocabularyConstraints to check against
        language: Target language
    
    Returns:
        ValidationResult
    """
    validator = VocabularyValidator(language)
    return validator.validate_vocabulary(passage, constraints)
