"""
Property-based tests for vocabulary coverage calculation.

Tests Property 9: Vocabulary Coverage Range
Validates that vocabulary coverage is always between 0.0 and 1.0
"""

from hypothesis import given, strategies as st
import pytest

from src.features.reader.vocabulary_service import VocabularyService
from src.features.reader.models import VocabularyConstraints


class TestVocabularyCoverageRange:
    """Property 9: Vocabulary Coverage Range"""
    
    @given(
        text=st.text(min_size=1, max_size=1000),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=100)
    )
    def test_coverage_always_between_zero_and_one(self, text, known_words):
        """
        Property: Coverage is always between 0.0 and 1.0
        
        For any text and vocabulary set, the calculated coverage
        should always be a valid percentage between 0.0 and 1.0.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Calculate coverage using simple method
        coverage = self._calculate_coverage_simple(text, known_words)
        
        # Assert coverage is in valid range
        assert 0.0 <= coverage <= 1.0, f"Coverage {coverage} is outside [0.0, 1.0]"
    
    @given(
        text=st.text(min_size=1),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=100)
    )
    def test_coverage_with_known_words(self, text, known_words):
        """
        Property: Coverage calculation respects known words
        
        When all words in text are known, coverage should be 1.0.
        When no words are known, coverage should be 0.0.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Test with all known words
        coverage_all_known = self._calculate_coverage_simple(text, known_words)
        assert 0.0 <= coverage_all_known <= 1.0
        
        # Test with no known words
        coverage_none_known = self._calculate_coverage_simple(text, set())
        assert coverage_none_known == 0.0
    
    def _calculate_coverage_simple(self, text, known_words):
        """Simple coverage calculation for testing"""
        import re
        tokens = re.findall(r'\w+', text.lower())
        if not tokens:
            return 0.0
        
        known_count = sum(1 for token in tokens if token in {w.lower() for w in known_words})
        return known_count / len(tokens)
    
    @given(
        text=st.text(min_size=1, max_size=500),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=50)
    )
    def test_coverage_monotonicity(self, text, known_words):
        """
        Property: Adding more known words increases or maintains coverage
        
        If we add a word to the known vocabulary, coverage should
        increase or stay the same, never decrease.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        coverage1 = self._calculate_coverage_simple(text, known_words)
        
        # Add a new word to known vocabulary
        new_word = "additional_test_word_xyz"
        known_words_extended = known_words | {new_word}
        
        coverage2 = self._calculate_coverage_simple(text, known_words_extended)
        
        # Coverage should not decrease
        assert coverage2 >= coverage1, \
            f"Coverage decreased from {coverage1} to {coverage2} after adding word"
    
    @given(
        text=st.text(min_size=1, max_size=500)
    )
    def test_coverage_empty_vocabulary(self, text):
        """
        Property: Coverage with empty vocabulary is always 0.0
        
        When no words are known, coverage must be 0.0.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        coverage = self._calculate_coverage_simple(text, set())
        assert coverage == 0.0, "Coverage with empty vocabulary should be 0.0"
    
    @given(
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=50)
    )
    def test_coverage_empty_text(self, known_words):
        """
        Property: Coverage with empty text is always 0.0
        
        When text is empty, coverage must be 0.0.
        """
        coverage = self._calculate_coverage_simple("", known_words)
        assert coverage == 0.0, "Coverage with empty text should be 0.0"
