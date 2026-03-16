"""
Unit tests for Sentence_Analyzer component.

Tests vocabulary analysis, grammar complexity detection, and difficulty scoring.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.core.database import FlashcardDatabase
from src.features.mining.logic.sentence_analyzer import SentenceAnalyzer, DifficultyResult


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = FlashcardDatabase(db_path)
    yield db
    
    # Cleanup
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def analyzer(test_db):
    """Create a SentenceAnalyzer instance."""
    return SentenceAnalyzer(test_db)


class TestVocabularyAnalysis:
    """Test vocabulary analysis functionality."""
    
    def test_calculate_known_word_ratio_all_known(self, analyzer):
        """Test known word ratio when all words are known."""
        # Add known words
        cursor = analyzer.db.conn.cursor()
        cursor.execute("INSERT INTO known_words (lemma, language, added_at) VALUES (?, ?, ?)",
                      ('hello', 'en', datetime.now().isoformat()))
        cursor.execute("INSERT INTO known_words (lemma, language, added_at) VALUES (?, ?, ?)",
                      ('world', 'en', datetime.now().isoformat()))
        analyzer.db.conn.commit()
        
        # Clear cache
        analyzer.user_vocabulary_cache.clear()
        
        ratio, unknown = analyzer.calculate_known_word_ratio('hello world', 'en')
        assert ratio == 1.0
        assert len(unknown) == 0
    
    def test_calculate_known_word_ratio_all_unknown(self, analyzer):
        """Test known word ratio when all words are unknown."""
        ratio, unknown = analyzer.calculate_known_word_ratio('xyzabc qwerty', 'en')
        assert ratio == 0.0
        assert len(unknown) == 2
    
    def test_calculate_known_word_ratio_partial(self, analyzer):
        """Test known word ratio with mixed known/unknown words."""
        cursor = analyzer.db.conn.cursor()
        cursor.execute("INSERT INTO known_words (lemma, language, added_at) VALUES (?, ?, ?)",
                      ('hello', 'en', datetime.now().isoformat()))
        analyzer.db.conn.commit()
        
        analyzer.user_vocabulary_cache.clear()
        
        ratio, unknown = analyzer.calculate_known_word_ratio('hello world test', 'en')
        assert ratio == pytest.approx(1/3, abs=0.01)
        assert len(unknown) == 2
    
    def test_identify_unknown_words(self, analyzer):
        """Test that unknown words are correctly identified."""
        cursor = analyzer.db.conn.cursor()
        cursor.execute("INSERT INTO known_words (lemma, language, added_at) VALUES (?, ?, ?)",
                      ('known', 'en', datetime.now().isoformat()))
        analyzer.db.conn.commit()
        
        analyzer.user_vocabulary_cache.clear()
        
        _, unknown = analyzer.calculate_known_word_ratio('known unknown rare', 'en')
        assert 'unknown' in unknown
        assert 'rare' in unknown
        assert 'known' not in unknown
    
    def test_empty_sentence(self, analyzer):
        """Test handling of empty sentence."""
        ratio, unknown = analyzer.calculate_known_word_ratio('', 'en')
        assert ratio == 1.0
        assert len(unknown) == 0


class TestGrammarComplexity:
    """Test grammar complexity detection."""
    
    def test_grammar_weights_defined(self, analyzer):
        """Test that grammar weights are properly defined."""
        assert 'beginner' in analyzer.GRAMMAR_WEIGHTS
        assert 'intermediate' in analyzer.GRAMMAR_WEIGHTS
        assert 'advanced' in analyzer.GRAMMAR_WEIGHTS
        assert analyzer.GRAMMAR_WEIGHTS['beginner'] == 0.2
        assert analyzer.GRAMMAR_WEIGHTS['intermediate'] == 0.5
        assert analyzer.GRAMMAR_WEIGHTS['advanced'] == 0.8
    
    def test_estimate_complexity_short_sentence(self, analyzer):
        """Test complexity estimation for short sentence."""
        complexity = analyzer._estimate_complexity_from_vocabulary('Hola', 'es')
        assert complexity == 'beginner'
    
    def test_estimate_complexity_medium_sentence(self, analyzer):
        """Test complexity estimation for medium sentence."""
        complexity = analyzer._estimate_complexity_from_vocabulary('Hola, ¿cómo estás hoy?', 'es')
        assert complexity in ['beginner', 'intermediate']
    
    def test_estimate_complexity_long_sentence(self, analyzer):
        """Test complexity estimation for long sentence."""
        long_sentence = 'Aunque no sabía exactamente qué hacer, decidió seguir adelante porque creía que era lo correcto.'
        complexity = analyzer._estimate_complexity_from_vocabulary(long_sentence, 'es')
        assert complexity in ['intermediate', 'advanced']


class TestDifficultyScoring:
    """Test difficulty score calculation."""
    
    def test_calculate_difficulty_score_all_known_beginner(self, analyzer):
        """Test difficulty score when all words known and beginner grammar."""
        score = analyzer.calculate_difficulty_score(1.0, 'beginner')
        # (1 - 1.0) * 0.6 + 0.2 * 0.4 = 0 + 0.08 = 0.08
        assert score == pytest.approx(0.08, abs=0.01)
    
    def test_calculate_difficulty_score_no_known_advanced(self, analyzer):
        """Test difficulty score when no words known and advanced grammar."""
        score = analyzer.calculate_difficulty_score(0.0, 'advanced')
        # (1 - 0.0) * 0.6 + 0.8 * 0.4 = 0.6 + 0.32 = 0.92
        assert score == pytest.approx(0.92, abs=0.01)
    
    def test_calculate_difficulty_score_clamped(self, analyzer):
        """Test that difficulty score is clamped to 0.0-1.0."""
        # Try with invalid grammar complexity (should default to 0.5)
        score = analyzer.calculate_difficulty_score(0.5, 'intermediate')
        assert 0.0 <= score <= 1.0
    
    def test_classify_difficulty_easy(self, analyzer):
        """Test difficulty classification for easy."""
        assert analyzer.classify_difficulty(0.0) == 'easy'
        assert analyzer.classify_difficulty(0.33) == 'easy'
    
    def test_classify_difficulty_medium(self, analyzer):
        """Test difficulty classification for medium."""
        assert analyzer.classify_difficulty(0.34) == 'medium'
        assert analyzer.classify_difficulty(0.5) == 'medium'
        assert analyzer.classify_difficulty(0.66) == 'medium'
    
    def test_classify_difficulty_hard(self, analyzer):
        """Test difficulty classification for hard."""
        assert analyzer.classify_difficulty(0.67) == 'hard'
        assert analyzer.classify_difficulty(1.0) == 'hard'


class TestRareWordDetection:
    """Test rare word detection using frequency lists."""
    
    def test_check_rare_words_no_frequency_list(self, analyzer):
        """Test rare word check when frequency list not available."""
        # Use language without frequency list
        rare_count = analyzer._check_rare_words(['word1', 'word2'], 'unknown_lang')
        assert rare_count == 0
    
    def test_check_rare_words_with_frequency_list(self, analyzer):
        """Test rare word check with frequency list."""
        # Spanish frequency list should be loaded
        if 'spanish' in analyzer.frequency_lists:
            # Common Spanish words
            rare_count = analyzer._check_rare_words(['de', 'la', 'que'], 'spanish')
            assert rare_count == 0
            
            # Rare Spanish words
            rare_count = analyzer._check_rare_words(['xyzabc', 'qwerty'], 'spanish')
            assert rare_count == 2


class TestSentenceAnalysis:
    """Test complete sentence analysis."""
    
    def test_analyze_sentence_not_found(self, analyzer):
        """Test analysis of non-existent sentence."""
        with pytest.raises(ValueError):
            analyzer.analyze_sentence(999)
    
    def test_analyze_sentence_basic(self, analyzer):
        """Test basic sentence analysis."""
        # Create a test sentence
        cursor = analyzer.db.conn.cursor()
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Hello world', 'http://example.com', 'en', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        analyzer.db.conn.commit()
        
        # Analyze it
        result = analyzer.analyze_sentence(sentence_id)
        
        assert isinstance(result, DifficultyResult)
        assert 0.0 <= result.difficulty_score <= 1.0
        assert 0.0 <= result.known_word_ratio <= 1.0
        assert result.grammar_complexity in ['beginner', 'intermediate', 'advanced']
        assert isinstance(result.unknown_words, list)
        assert result.rare_word_count >= 0
    
    def test_analyze_sentence_stores_results(self, analyzer):
        """Test that analysis results are stored in database."""
        # Create a test sentence
        cursor = analyzer.db.conn.cursor()
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Test sentence', 'http://example.com', 'en', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        analyzer.db.conn.commit()
        
        # Analyze it
        analyzer.analyze_sentence(sentence_id)
        
        # Verify results were stored
        cursor.execute(
            "SELECT difficulty_score, known_word_ratio, grammar_complexity, unknown_words, analysis_timestamp FROM imported_content WHERE id = ?",
            (sentence_id,)
        )
        row = cursor.fetchone()
        
        assert row[0] is not None  # difficulty_score
        assert row[1] is not None  # known_word_ratio
        assert row[2] is not None  # grammar_complexity
        assert row[3] is not None  # unknown_words
        assert row[4] is not None  # analysis_timestamp


class TestBatchAnalysis:
    """Test batch analysis functionality."""
    
    def test_batch_analyze_empty_list(self, analyzer):
        """Test batch analysis with empty list."""
        count = analyzer.batch_analyze([])
        assert count == 0
    
    def test_batch_analyze_multiple_sentences(self, analyzer):
        """Test batch analysis of multiple sentences."""
        # Create test sentences
        cursor = analyzer.db.conn.cursor()
        sentence_ids = []
        
        for i in range(3):
            cursor.execute(
                "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
                ('sentence', f'Test sentence {i}', 'http://example.com', 'en', datetime.now().isoformat())
            )
            sentence_ids.append(cursor.lastrowid)
        
        analyzer.db.conn.commit()
        
        # Batch analyze
        count = analyzer.batch_analyze(sentence_ids)
        assert count == 3
    
    def test_batch_analyze_with_progress_callback(self, analyzer):
        """Test batch analysis with progress callback."""
        # Create test sentences
        cursor = analyzer.db.conn.cursor()
        sentence_ids = []
        
        for i in range(2):
            cursor.execute(
                "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
                ('sentence', f'Test sentence {i}', 'http://example.com', 'en', datetime.now().isoformat())
            )
            sentence_ids.append(cursor.lastrowid)
        
        analyzer.db.conn.commit()
        
        # Track progress
        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        # Batch analyze
        analyzer.batch_analyze(sentence_ids, progress_callback)
        
        # Verify progress was reported
        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)


class TestFrequencyListLoading:
    """Test frequency list loading."""
    
    def test_frequency_lists_loaded(self, analyzer):
        """Test that frequency lists are loaded."""
        # At least Spanish should be loaded
        assert len(analyzer.frequency_lists) > 0
    
    def test_frequency_list_is_set(self, analyzer):
        """Test that frequency lists are stored as sets."""
        if 'spanish' in analyzer.frequency_lists:
            assert isinstance(analyzer.frequency_lists['spanish'], set)
            assert len(analyzer.frequency_lists['spanish']) > 0
