"""
Property-based tests for validation determinism.

Tests Property 6: Validation Determinism
Validates that repeated validation calls return identical results
"""

from hypothesis import given, strategies as st, settings, HealthCheck
import pytest

from src.features.reader.validator import VocabularyValidator
from src.features.reader.models import StoryPassage, NewWord, Choice, VocabularyConstraints


class TestValidationDeterminism:
    """Property 6: Validation Determinism"""
    
    @pytest.fixture
    def validator(self):
        """Create a VocabularyValidator instance"""
        return VocabularyValidator(language="korean")
    
    @given(
        text=st.text(min_size=1, max_size=500),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=50)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validation_determinism(self, validator, text, known_words):
        """
        Property: Validation is deterministic
        
        For any given passage and vocabulary constraints, repeated
        validation calls should return identical results.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Create a passage
        try:
            passage = StoryPassage(
                session_id=1,
                passage_number=1,
                story_text=text,
                new_words=[NewWord("test", "test", text if "test" in text else text + " test")],
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
        except ValueError:
            pytest.skip("Invalid passage")
        
        # Create constraints
        constraints = VocabularyConstraints(
            known_words=known_words,
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        # Validate multiple times
        result1 = validator.validate_vocabulary(passage, constraints)
        result2 = validator.validate_vocabulary(passage, constraints)
        result3 = validator.validate_vocabulary(passage, constraints)
        
        # All results should be identical
        assert result1.is_valid == result2.is_valid == result3.is_valid
        assert result1.coverage == result2.coverage == result3.coverage
        assert result1.unknown_words == result2.unknown_words == result3.unknown_words
        assert result1.message == result2.message == result3.message
    
    @given(
        text=st.text(min_size=1, max_size=500),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=50)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coverage_calculation_determinism(self, validator, text, known_words):
        """
        Property: Coverage calculation is deterministic
        
        Repeated coverage calculations for the same text and vocabulary
        should always return the same value.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Calculate coverage multiple times
        coverage1 = validator.calculate_coverage(text, known_words)
        coverage2 = validator.calculate_coverage(text, known_words)
        coverage3 = validator.calculate_coverage(text, known_words)
        
        # All should be identical
        assert coverage1 == coverage2 == coverage3
    
    @given(
        text=st.text(min_size=1, max_size=500),
        known_words=st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=50)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unknown_words_extraction_determinism(self, validator, text, known_words):
        """
        Property: Unknown word extraction is deterministic
        
        Repeated extraction of unknown words should return the same list
        (though order may vary, the set should be identical).
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Extract unknown words multiple times
        unknown1 = set(validator.extract_unknown_words(text, known_words))
        unknown2 = set(validator.extract_unknown_words(text, known_words))
        unknown3 = set(validator.extract_unknown_words(text, known_words))
        
        # All should be identical sets
        assert unknown1 == unknown2 == unknown3
    
    @given(
        text=st.text(min_size=1, max_size=500)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tokenization_determinism(self, validator, text):
        """
        Property: Tokenization is deterministic
        
        Repeated tokenization of the same text should produce identical results.
        """
        if not text or not text.strip():
            pytest.skip("Empty text")
        
        # Tokenize multiple times
        tokens1 = validator.tokenize(text)
        tokens2 = validator.tokenize(text)
        tokens3 = validator.tokenize(text)
        
        # All should be identical
        assert tokens1 == tokens2 == tokens3
    
    @given(
        word=st.text(min_size=1, max_size=20)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_lemmatization_determinism(self, validator, word):
        """
        Property: Lemmatization is deterministic
        
        Repeated lemmatization of the same word should produce identical results.
        """
        if not word or not word.strip():
            pytest.skip("Empty word")
        
        # Lemmatize multiple times
        lemma1 = validator.lemmatize(word)
        lemma2 = validator.lemmatize(word)
        lemma3 = validator.lemmatize(word)
        
        # All should be identical
        assert lemma1 == lemma2 == lemma3
    
    def test_validation_idempotence(self, validator):
        """
        Property: Validation is idempotent
        
        Validating the same passage multiple times should not change
        the passage or produce different results.
        """
        passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="This is a test passage with test word",
            new_words=[NewWord("test", "test", "This is a test passage with test word")],
            choices=[Choice(1, "choice1"), Choice(2, "choice2")],
            created_at="2024-01-01T00:00:00"
        )
        
        constraints = VocabularyConstraints(
            known_words={"this", "is", "a", "passage", "with", "word"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        # Validate multiple times
        result1 = validator.validate_vocabulary(passage, constraints)
        result2 = validator.validate_vocabulary(passage, constraints)
        
        # Results should be identical
        assert result1.is_valid == result2.is_valid
        assert result1.coverage == result2.coverage
        
        # Passage should not be modified
        assert passage.story_text == "This is a test passage with test word"
        assert len(passage.new_words) == 1
