"""
Unit tests for DifficultyCalculator.

Tests difficulty score calculation, rating assignment, and component scores.
"""

import pytest
from hypothesis import given, strategies as st
from src.features.reader.difficulty_calculator import DifficultyCalculator


class TestDifficultyCalculator:
    """Test suite for DifficultyCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Create a DifficultyCalculator instance."""
        return DifficultyCalculator()
    
    def test_calculate_difficulty_easy_text(self, calculator):
        """Test difficulty calculation for easy text."""
        # Simple text with short words and sentences
        easy_text = "I like cats. Cats are nice. They are soft."
        
        result = calculator.calculate_difficulty(easy_text)
        
        assert 'difficulty_score' in result
        assert 'difficulty_rating' in result
        assert 0.0 <= result['difficulty_score'] <= 1.0
        assert result['difficulty_rating'] in ['easy', 'medium', 'hard']
        # Easy text should have low score
        assert result['difficulty_score'] < 0.5
    
    def test_calculate_difficulty_hard_text(self, calculator):
        """Test difficulty calculation for hard text."""
        # Complex text with long words and complex sentences
        hard_text = (
            "The implementation of sophisticated algorithms necessitates "
            "comprehensive understanding of computational complexity theory, "
            "which encompasses various methodologies and paradigms that have "
            "been extensively researched throughout the academic community."
        )
        
        result = calculator.calculate_difficulty(hard_text)
        
        assert 'difficulty_score' in result
        assert 'difficulty_rating' in result
        assert 0.0 <= result['difficulty_score'] <= 1.0
        # Hard text should have high score
        assert result['difficulty_score'] > 0.5
    
    def test_difficulty_score_range(self, calculator):
        """Test that difficulty scores are always in [0.0, 1.0] range."""
        test_texts = [
            "Hi.",
            "The cat sat on the mat.",
            "Although the implementation was complex, the results were satisfactory.",
            "A" * 1000,  # Very long single word
            "a " * 1000,  # Many short words
        ]
        
        for text in test_texts:
            result = calculator.calculate_difficulty(text)
            assert 0.0 <= result['difficulty_score'] <= 1.0
    
    def test_difficulty_rating_assignment(self, calculator):
        """Test that difficulty ratings are assigned correctly."""
        # Test boundary cases
        assert calculator._assign_rating(0.0) == 'easy'
        assert calculator._assign_rating(0.32) == 'easy'
        assert calculator._assign_rating(0.33) == 'medium'
        assert calculator._assign_rating(0.5) == 'medium'
        assert calculator._assign_rating(0.66) == 'medium'
        assert calculator._assign_rating(0.67) == 'hard'
        assert calculator._assign_rating(1.0) == 'hard'
    
    def test_rating_matches_score(self, calculator):
        """Test that rating assignment matches score thresholds."""
        test_texts = [
            "I am happy. You are nice.",  # Should be easy
            "The quick brown fox jumps over the lazy dog every morning.",  # Should be medium
            "Notwithstanding the aforementioned considerations, the implementation "
            "requires substantial modifications.",  # Should be hard
        ]
        
        for text in test_texts:
            result = calculator.calculate_difficulty(text)
            score = result['difficulty_score']
            rating = result['difficulty_rating']
            
            # Verify rating matches score thresholds
            if score < 0.33:
                assert rating == 'easy'
            elif score < 0.67:
                assert rating == 'medium'
            else:
                assert rating == 'hard'
    
    def test_component_scores_present(self, calculator):
        """Test that all component scores are included in result."""
        text = "The cat sat on the mat."
        
        result = calculator.calculate_difficulty(text)
        
        assert 'vocab_score' in result
        assert 'sentence_length_score' in result
        assert 'grammar_score' in result
        assert 0.0 <= result['vocab_score'] <= 1.0
        assert 0.0 <= result['sentence_length_score'] <= 1.0
        assert 0.0 <= result['grammar_score'] <= 1.0
    
    def test_metrics_included(self, calculator):
        """Test that raw metrics are included in result."""
        text = "The cat sat on the mat. The dog ran in the park."
        
        result = calculator.calculate_difficulty(text)
        
        assert 'metrics' in result
        metrics = result['metrics']
        
        assert 'word_count' in metrics
        assert 'sentence_count' in metrics
        assert 'unique_word_count' in metrics
        assert 'avg_word_length' in metrics
        assert 'avg_sentence_length' in metrics
        assert 'unique_word_ratio' in metrics
        
        # Verify metrics are reasonable
        assert metrics['word_count'] > 0
        assert metrics['sentence_count'] == 2
        assert metrics['unique_word_count'] <= metrics['word_count']
        assert metrics['avg_word_length'] > 0
        assert metrics['avg_sentence_length'] > 0
        assert 0.0 <= metrics['unique_word_ratio'] <= 1.0
    
    def test_empty_content(self, calculator):
        """Test handling of empty content."""
        result = calculator.calculate_difficulty("")
        
        assert result['difficulty_score'] == 0.0
        assert result['difficulty_rating'] == 'easy'
        assert result['vocab_score'] == 0.0
        assert result['sentence_length_score'] == 0.0
        assert result['grammar_score'] == 0.0
    
    def test_whitespace_only_content(self, calculator):
        """Test handling of whitespace-only content."""
        result = calculator.calculate_difficulty("   \n\n\t  ")
        
        assert result['difficulty_score'] == 0.0
        assert result['difficulty_rating'] == 'easy'
    
    def test_extract_words(self, calculator):
        """Test word extraction."""
        text = "Hello, world! How are you?"
        words = calculator._extract_words(text)
        
        assert len(words) == 5
        assert 'Hello' in words
        assert 'world' in words
        assert 'How' in words
        assert 'are' in words
        assert 'you' in words
        # Punctuation should be excluded
        assert ',' not in words
        assert '!' not in words
        assert '?' not in words
    
    def test_extract_words_with_contractions(self, calculator):
        """Test that contractions are handled correctly."""
        text = "I don't think it's working."
        words = calculator._extract_words(text)
        
        # Contractions should be kept as single words
        assert "don't" in words
        assert "it's" in words
    
    def test_extract_sentences(self, calculator):
        """Test sentence extraction."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = calculator._extract_sentences(text)
        
        assert len(sentences) == 3
        assert 'First sentence' in sentences
        assert 'Second sentence' in sentences
        assert 'Third sentence' in sentences
    
    def test_vocab_complexity_short_words(self, calculator):
        """Test vocabulary complexity with short words."""
        # Short, simple words
        words = ['I', 'am', 'a', 'cat', 'you', 'are', 'a', 'dog']
        score = calculator._calculate_vocab_complexity(words)
        
        # Should have low to medium complexity
        assert score <= 0.6
    
    def test_vocab_complexity_long_words(self, calculator):
        """Test vocabulary complexity with long words."""
        # Long, complex words
        words = ['implementation', 'sophisticated', 'comprehensive', 'methodology']
        score = calculator._calculate_vocab_complexity(words)
        
        # Should have high complexity
        assert score > 0.5
    
    def test_sentence_length_complexity_short(self, calculator):
        """Test sentence length complexity with short sentences."""
        words = ['I', 'am', 'happy']
        sentences = ['I am happy']
        score = calculator._calculate_sentence_length_complexity(words, sentences)
        
        # Should have low complexity
        assert score < 0.5
    
    def test_sentence_length_complexity_long(self, calculator):
        """Test sentence length complexity with long sentences."""
        words = ['word'] * 30  # 30 words in one sentence
        sentences = [' '.join(words)]
        score = calculator._calculate_sentence_length_complexity(words, sentences)
        
        # Should have high complexity
        assert score > 0.5
    
    def test_grammar_complexity_simple(self, calculator):
        """Test grammar complexity with simple sentences."""
        sentences = ['I like cats', 'You like dogs']
        score = calculator._calculate_grammar_complexity(sentences)
        
        # Should have low complexity (no subordinate clauses)
        assert score < 0.5
    
    def test_grammar_complexity_complex(self, calculator):
        """Test grammar complexity with complex sentences."""
        sentences = [
            'Although I like cats, which are soft, I also like dogs because they are loyal',
            'The book that I read, which was interesting, was written by an author who lives nearby'
        ]
        score = calculator._calculate_grammar_complexity(sentences)
        
        # Should have higher complexity (many subordinate markers)
        assert score > 0.3
    
    def test_unicode_content(self, calculator):
        """Test handling of Unicode content (non-English languages)."""
        # Korean text
        korean_text = "안녕하세요. 저는 한국어를 공부합니다."
        result = calculator.calculate_difficulty(korean_text)
        
        assert 'difficulty_score' in result
        assert 0.0 <= result['difficulty_score'] <= 1.0
        assert result['difficulty_rating'] in ['easy', 'medium', 'hard']
    
    def test_mixed_language_content(self, calculator):
        """Test handling of mixed language content."""
        mixed_text = "Hello world. 안녕하세요. Bonjour le monde."
        result = calculator.calculate_difficulty(mixed_text)
        
        assert 'difficulty_score' in result
        assert 0.0 <= result['difficulty_score'] <= 1.0
    
    def test_language_parameter(self, calculator):
        """Test that language parameter is accepted (even if not used yet)."""
        text = "The cat sat on the mat."
        
        result_en = calculator.calculate_difficulty(text, language='en')
        result_ko = calculator.calculate_difficulty(text, language='ko')
        
        # Currently language doesn't affect calculation, but parameter should work
        assert 'difficulty_score' in result_en
        assert 'difficulty_score' in result_ko
    
    def test_consistent_results(self, calculator):
        """Test that same text produces consistent results."""
        text = "The quick brown fox jumps over the lazy dog."
        
        result1 = calculator.calculate_difficulty(text)
        result2 = calculator.calculate_difficulty(text)
        
        assert result1['difficulty_score'] == result2['difficulty_score']
        assert result1['difficulty_rating'] == result2['difficulty_rating']
    
    def test_score_precision(self, calculator):
        """Test that scores are rounded to reasonable precision."""
        text = "The cat sat on the mat."
        result = calculator.calculate_difficulty(text)
        
        # Scores should be rounded to 3 decimal places
        assert len(str(result['difficulty_score']).split('.')[-1]) <= 3
        assert len(str(result['vocab_score']).split('.')[-1]) <= 3
        assert len(str(result['sentence_length_score']).split('.')[-1]) <= 3
        assert len(str(result['grammar_score']).split('.')[-1]) <= 3


class TestDifficultyScoreRangeProperty:
    """
    Property-based tests for difficulty score range validation.
    
    Property 6: Difficulty Score Range
    Validates: Requirements 1.6, 14.1, 14.2
    
    This test verifies that for ANY arbitrary text input:
    1. difficulty_score is always in the range [0.0, 1.0]
    2. difficulty_rating is always one of ['easy', 'medium', 'hard']
    3. The rating correctly corresponds to the score thresholds
    """
    
    @given(
        content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=0,
            max_size=10000
        )
    )
    def test_property_difficulty_score_range(self, content):
        """
        Property test: Difficulty score is always in [0.0, 1.0] range.
        
        For ANY text content (including edge cases like empty strings,
        very long texts, special characters, etc.), the difficulty_score
        must be between 0.0 and 1.0 inclusive.
        
        Validates Requirements:
        - 1.6: Calculate difficulty score for imported content
        - 14.1: Analyze vocabulary complexity to calculate difficulty score
        - 14.2: Assign difficulty rating based on score
        """
        calculator = DifficultyCalculator()
        result = calculator.calculate_difficulty(content)
        
        # Core property: score must be in valid range
        assert 0.0 <= result['difficulty_score'] <= 1.0, (
            f"Difficulty score {result['difficulty_score']} is outside [0.0, 1.0] range "
            f"for content: {content[:100]}..."
        )
    
    @given(
        content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=0,
            max_size=10000
        )
    )
    def test_property_difficulty_rating_valid(self, content):
        """
        Property test: Difficulty rating is always one of the valid values.
        
        For ANY text content, the difficulty_rating must be exactly one of:
        'easy', 'medium', or 'hard'.
        
        Validates Requirements:
        - 14.2: Assign difficulty rating of easy, medium, or hard
        """
        calculator = DifficultyCalculator()
        result = calculator.calculate_difficulty(content)
        
        valid_ratings = ['easy', 'medium', 'hard']
        assert result['difficulty_rating'] in valid_ratings, (
            f"Difficulty rating '{result['difficulty_rating']}' is not in {valid_ratings} "
            f"for content: {content[:100]}..."
        )
    
    @given(
        content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=1,  # At least 1 character to get meaningful scores
            max_size=10000
        )
    )
    def test_property_rating_matches_score_thresholds(self, content):
        """
        Property test: Rating assignment matches score thresholds.
        
        For ANY text content, the difficulty_rating must correctly correspond
        to the difficulty_score according to the defined thresholds:
        - [0.0, 0.33) -> 'easy'
        - [0.33, 0.67) -> 'medium'
        - [0.67, 1.0] -> 'hard'
        
        Validates Requirements:
        - 14.2: Assign difficulty rating based on score thresholds
        """
        calculator = DifficultyCalculator()
        result = calculator.calculate_difficulty(content)
        
        score = result['difficulty_score']
        rating = result['difficulty_rating']
        
        # Verify rating matches score thresholds
        if score < 0.33:
            expected_rating = 'easy'
        elif score < 0.67:
            expected_rating = 'medium'
        else:
            expected_rating = 'hard'
        
        assert rating == expected_rating, (
            f"Rating '{rating}' does not match expected '{expected_rating}' "
            f"for score {score} (content: {content[:100]}...)"
        )
    
    @given(
        content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=0,
            max_size=10000
        )
    )
    def test_property_component_scores_in_range(self, content):
        """
        Property test: All component scores are in [0.0, 1.0] range.
        
        For ANY text content, all component scores (vocab_score,
        sentence_length_score, grammar_score) must be in [0.0, 1.0].
        
        Validates Requirements:
        - 14.1: Calculate difficulty based on vocabulary complexity,
                sentence length, and grammatical complexity
        """
        calculator = DifficultyCalculator()
        result = calculator.calculate_difficulty(content)
        
        # All component scores must be in valid range
        assert 0.0 <= result['vocab_score'] <= 1.0, (
            f"vocab_score {result['vocab_score']} is outside [0.0, 1.0] range"
        )
        assert 0.0 <= result['sentence_length_score'] <= 1.0, (
            f"sentence_length_score {result['sentence_length_score']} is outside [0.0, 1.0] range"
        )
        assert 0.0 <= result['grammar_score'] <= 1.0, (
            f"grammar_score {result['grammar_score']} is outside [0.0, 1.0] range"
        )
    
    @given(
        # Generate realistic text with words and sentences
        content=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')),
            min_size=10,
            max_size=1000
        ).filter(lambda x: len(x.strip()) > 0)
    )
    def test_property_result_structure(self, content):
        """
        Property test: Result always contains required fields.
        
        For ANY text content, the result dictionary must contain all
        required fields with correct types.
        """
        calculator = DifficultyCalculator()
        result = calculator.calculate_difficulty(content)
        
        # Required fields must be present
        assert 'difficulty_score' in result
        assert 'difficulty_rating' in result
        assert 'vocab_score' in result
        assert 'sentence_length_score' in result
        assert 'grammar_score' in result
        assert 'metrics' in result
        
        # Types must be correct
        assert isinstance(result['difficulty_score'], (int, float))
        assert isinstance(result['difficulty_rating'], str)
        assert isinstance(result['vocab_score'], (int, float))
        assert isinstance(result['sentence_length_score'], (int, float))
        assert isinstance(result['grammar_score'], (int, float))
        assert isinstance(result['metrics'], dict)


class TestDifficultyRatingAssignmentProperty:
    """
    Property-based tests for difficulty rating assignment.
    
    Property 37: Difficulty Rating Assignment
    Validates: Requirements 14.2
    
    This test verifies that for ANY difficulty score in [0.0, 1.0]:
    1. Score [0.0, 0.33) maps to 'easy'
    2. Score [0.33, 0.67) maps to 'medium'
    3. Score [0.67, 1.0] maps to 'hard'
    
    This property ensures the rating assignment function correctly implements
    the specified thresholds for all possible score values.
    """
    
    @given(
        score=st.floats(min_value=0.0, max_value=0.33, exclude_max=True)
    )
    def test_property_easy_rating_assignment(self, score):
        """
        Property test: Scores in [0.0, 0.33) always map to 'easy'.
        
        For ANY score in the range [0.0, 0.33), the rating assignment
        function must return 'easy'.
        
        Validates Requirement 14.2: Assign difficulty rating based on score
        """
        calculator = DifficultyCalculator()
        rating = calculator._assign_rating(score)
        
        assert rating == 'easy', (
            f"Score {score} in range [0.0, 0.33) should map to 'easy', "
            f"but got '{rating}'"
        )
    
    @given(
        score=st.floats(min_value=0.33, max_value=0.67, exclude_max=True)
    )
    def test_property_medium_rating_assignment(self, score):
        """
        Property test: Scores in [0.33, 0.67) always map to 'medium'.
        
        For ANY score in the range [0.33, 0.67), the rating assignment
        function must return 'medium'.
        
        Validates Requirement 14.2: Assign difficulty rating based on score
        """
        calculator = DifficultyCalculator()
        rating = calculator._assign_rating(score)
        
        assert rating == 'medium', (
            f"Score {score} in range [0.33, 0.67) should map to 'medium', "
            f"but got '{rating}'"
        )
    
    @given(
        score=st.floats(min_value=0.67, max_value=1.0)
    )
    def test_property_hard_rating_assignment(self, score):
        """
        Property test: Scores in [0.67, 1.0] always map to 'hard'.
        
        For ANY score in the range [0.67, 1.0], the rating assignment
        function must return 'hard'.
        
        Validates Requirement 14.2: Assign difficulty rating based on score
        """
        calculator = DifficultyCalculator()
        rating = calculator._assign_rating(score)
        
        assert rating == 'hard', (
            f"Score {score} in range [0.67, 1.0] should map to 'hard', "
            f"but got '{rating}'"
        )
    
    @given(
        score=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_property_all_scores_map_to_valid_rating(self, score):
        """
        Property test: All scores in [0.0, 1.0] map to a valid rating.
        
        For ANY score in the valid range [0.0, 1.0], the rating assignment
        function must return one of the three valid ratings: 'easy', 'medium', or 'hard'.
        
        Validates Requirement 14.2: Assign difficulty rating based on score
        """
        calculator = DifficultyCalculator()
        rating = calculator._assign_rating(score)
        
        valid_ratings = ['easy', 'medium', 'hard']
        assert rating in valid_ratings, (
            f"Score {score} produced invalid rating '{rating}'. "
            f"Expected one of {valid_ratings}"
        )
    
    @given(
        score=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_property_rating_assignment_is_deterministic(self, score):
        """
        Property test: Rating assignment is deterministic.
        
        For ANY score, calling the rating assignment function multiple times
        with the same score must always return the same rating.
        
        Validates Requirement 14.2: Consistent rating assignment
        """
        calculator = DifficultyCalculator()
        
        rating1 = calculator._assign_rating(score)
        rating2 = calculator._assign_rating(score)
        rating3 = calculator._assign_rating(score)
        
        assert rating1 == rating2 == rating3, (
            f"Rating assignment for score {score} is not deterministic: "
            f"got {rating1}, {rating2}, {rating3}"
        )
    
    def test_boundary_values_exact(self):
        """
        Test exact boundary values for rating assignment.
        
        This test verifies the precise boundary behavior at the threshold values:
        - 0.0 (minimum) -> 'easy'
        - 0.33 (easy/medium boundary) -> 'medium'
        - 0.67 (medium/hard boundary) -> 'hard'
        - 1.0 (maximum) -> 'hard'
        
        Validates Requirement 14.2: Correct threshold implementation
        """
        calculator = DifficultyCalculator()
        
        # Test exact boundaries
        assert calculator._assign_rating(0.0) == 'easy', "Score 0.0 should be 'easy'"
        assert calculator._assign_rating(0.32999999) == 'easy', "Score just below 0.33 should be 'easy'"
        assert calculator._assign_rating(0.33) == 'medium', "Score 0.33 should be 'medium'"
        assert calculator._assign_rating(0.66999999) == 'medium', "Score just below 0.67 should be 'medium'"
        assert calculator._assign_rating(0.67) == 'hard', "Score 0.67 should be 'hard'"
        assert calculator._assign_rating(1.0) == 'hard', "Score 1.0 should be 'hard'"
    
    @given(
        score=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_property_rating_matches_threshold_logic(self, score):
        """
        Property test: Rating assignment matches threshold logic.
        
        For ANY score in [0.0, 1.0], verify that the rating returned by
        _assign_rating() matches the expected rating based on threshold logic.
        
        This is a comprehensive test that validates the complete rating
        assignment specification.
        
        Validates Requirement 14.2: Complete rating assignment specification
        """
        calculator = DifficultyCalculator()
        rating = calculator._assign_rating(score)
        
        # Determine expected rating based on thresholds
        if score < 0.33:
            expected = 'easy'
        elif score < 0.67:
            expected = 'medium'
        else:
            expected = 'hard'
        
        assert rating == expected, (
            f"Score {score} should map to '{expected}' but got '{rating}'. "
            f"Threshold logic: [0.0, 0.33) -> easy, [0.33, 0.67) -> medium, [0.67, 1.0] -> hard"
        )

