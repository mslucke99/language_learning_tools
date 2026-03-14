"""
Unit tests for VocabularyService.

Tests vocabulary extraction, caching, and coverage calculation.
"""

import pytest
import tempfile
import sqlite3
from unittest.mock import Mock, MagicMock, patch

from src.features.reader.vocabulary_service import VocabularyService


class TestVocabularyService:
    """Test cases for VocabularyService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database for testing"""
        db = Mock()
        db.conn = Mock()
        db.get_all_known_words = Mock(return_value=[])
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a VocabularyService instance with mock database"""
        return VocabularyService(mock_db)
    
    def test_get_known_words_empty_vocabulary(self, service, mock_db):
        """Test getting known words when vocabulary is empty"""
        mock_db.get_all_known_words.return_value = []
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        words = service.get_known_words("korean")
        
        assert isinstance(words, list)
        assert len(words) == 0
    
    def test_get_known_words_with_vocabulary(self, service, mock_db):
        """Test getting known words from database"""
        # Mock the database responses
        mock_db.get_all_known_words.return_value = [
            {"lemma": "학교"},
            {"lemma": "책"},
            {"lemma": "친구"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        words = service.get_known_words("korean")
        
        assert len(words) == 3
        assert "학교" in words
        assert "책" in words
        assert "친구" in words
    
    def test_get_known_words_large_vocabulary(self, service, mock_db):
        """Test getting known words with large vocabulary (1000+ words)"""
        # Create 1000 mock words
        large_vocab = [{"lemma": f"word{i}"} for i in range(1000)]
        mock_db.get_all_known_words.return_value = large_vocab
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        words = service.get_known_words("korean")
        
        assert len(words) == 1000
        assert "word0" in words
        assert "word999" in words
    
    def test_get_known_words_unicode_characters(self, service, mock_db):
        """Test getting known words with special characters and Unicode"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "학교"},  # Korean
            {"lemma": "escuela"},  # Spanish
            {"lemma": "学校"},  # Japanese
            {"lemma": "café"},  # Accented
            {"lemma": "naïve"}  # Diaeresis
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        words = service.get_known_words("korean")
        
        assert len(words) == 5
        assert "학교" in words
        assert "escuela" in words
        assert "学校" in words
        assert "café" in words
        assert "naïve" in words
    
    def test_get_known_words_caching(self, service, mock_db):
        """Test that vocabulary is cached after first retrieval"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word1"},
            {"lemma": "word2"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        # First call
        words1 = service.get_known_words("korean")
        
        # Second call should use cache
        words2 = service.get_known_words("korean")
        
        # Both should be identical
        assert words1 == words2
        
        # Database should only be queried once
        assert mock_db.get_all_known_words.call_count == 1
    
    def test_get_known_words_different_languages(self, service, mock_db):
        """Test that different languages have separate caches"""
        def get_words_side_effect(language):
            if language == "korean":
                return [{"lemma": "한국어"}]
            elif language == "spanish":
                return [{"lemma": "español"}]
            return []
        
        mock_db.get_all_known_words.side_effect = get_words_side_effect
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        korean_words = service.get_known_words("korean")
        spanish_words = service.get_known_words("spanish")
        
        assert "한국어" in korean_words
        assert "español" in spanish_words
        assert len(korean_words) == 1
        assert len(spanish_words) == 1
    
    def test_get_known_word_count(self, service, mock_db):
        """Test getting count of known words"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word1"},
            {"lemma": "word2"},
            {"lemma": "word3"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        count = service.get_known_word_count("korean")
        
        assert count == 3
    
    def test_is_word_known_true(self, service, mock_db):
        """Test checking if a word is known (positive case)"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "학교"},
            {"lemma": "책"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        assert service.is_word_known("학교", "korean") is True
        assert service.is_word_known("책", "korean") is True
    
    def test_is_word_known_false(self, service, mock_db):
        """Test checking if a word is known (negative case)"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "학교"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        assert service.is_word_known("unknown", "korean") is False
    
    def test_is_word_known_case_insensitive(self, service, mock_db):
        """Test that word lookup is case-insensitive"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "School"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        assert service.is_word_known("school", "korean") is True
        assert service.is_word_known("SCHOOL", "korean") is True
        assert service.is_word_known("School", "korean") is True
    
    def test_get_vocabulary_coverage_all_known(self, service, mock_db):
        """Test coverage when all words are known"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "hello"},
            {"lemma": "world"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        coverage = service.get_vocabulary_coverage("hello world", "korean")
        
        assert coverage == 1.0
    
    def test_get_vocabulary_coverage_none_known(self, service, mock_db):
        """Test coverage when no words are known"""
        mock_db.get_all_known_words.return_value = []
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        coverage = service.get_vocabulary_coverage("hello world", "korean")
        
        assert coverage == 0.0
    
    def test_get_vocabulary_coverage_partial(self, service, mock_db):
        """Test coverage with partial known vocabulary"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "hello"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        coverage = service.get_vocabulary_coverage("hello world test", "korean")
        
        # 1 known word out of 3 = 0.333...
        assert 0.3 < coverage < 0.4
    
    def test_get_vocabulary_coverage_empty_text(self, service, mock_db):
        """Test coverage with empty text"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        coverage = service.get_vocabulary_coverage("", "korean")
        
        assert coverage == 0.0
    
    def test_get_vocabulary_coverage_clamped(self, service, mock_db):
        """Test that coverage is clamped to [0.0, 1.0]"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        # Coverage should never exceed 1.0
        coverage = service.get_vocabulary_coverage("word word word", "korean")
        
        assert coverage <= 1.0
        assert coverage >= 0.0
    
    def test_clear_cache_all(self, service, mock_db):
        """Test clearing entire cache"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word1"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        # Populate cache
        service.get_known_words("korean")
        service.get_known_words("spanish")
        
        # Clear all cache
        service.clear_cache()
        
        # Cache should be empty
        assert len(service._cache) == 0
    
    def test_clear_cache_language_specific(self, service, mock_db):
        """Test clearing cache for specific language"""
        mock_db.get_all_known_words.return_value = [
            {"lemma": "word1"}
        ]
        mock_db.conn.cursor.return_value.fetchall.return_value = []
        
        # Populate cache for two languages
        service.get_known_words("korean")
        service.get_known_words("spanish")
        
        # Clear only Korean cache
        service.clear_cache("korean")
        
        # Korean cache should be cleared, Spanish should remain
        assert len(service._cache) == 1
        assert any("spanish" in key for key in service._cache.keys())
    
    def test_add_encountered_words(self, service, mock_db):
        """Test tracking encountered words in a session"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ('[]',)
        mock_db.conn.cursor.return_value = mock_cursor
        
        words = [
            {"word": "새로운", "translation": "new"},
            {"word": "단어", "translation": "word"}
        ]
        
        service.add_encountered_words(1, words)
        
        # Verify database was updated
        mock_cursor.execute.assert_called()
    
    def test_add_encountered_words_empty_list(self, service, mock_db):
        """Test that adding empty word list doesn't update database"""
        mock_cursor = Mock()
        mock_db.conn.cursor.return_value = mock_cursor
        
        service.add_encountered_words(1, [])
        
        # Database should not be queried
        mock_cursor.execute.assert_not_called()
    
    def test_extract_word_from_question_plain(self, service):
        """Test extracting word from plain question format"""
        word = service._extract_word_from_question("학교")
        assert word == "학교"
    
    def test_extract_word_from_question_with_context(self, service):
        """Test extracting word from question with context"""
        word = service._extract_word_from_question("학교 (in sentence: ...)")
        assert word == "학교"
    
    def test_extract_word_from_question_with_translation(self, service):
        """Test extracting word from question with translation"""
        word = service._extract_word_from_question("학교 - school")
        assert word == "학교"
    
    def test_extract_word_from_question_empty(self, service):
        """Test extracting word from empty question"""
        word = service._extract_word_from_question("")
        assert word == ""
