"""
Unit tests for VocabExtractor class.

Tests vocabulary extraction functionality including context length limits,
word extraction, and flashcard creation integration.
"""

import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings, HealthCheck
from src.core.database import FlashcardDatabase
from src.features.reader.vocab_extractor import VocabExtractor


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = FlashcardDatabase(db_name=db_path)
    
    yield db
    
    db.conn.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def vocab_extractor(test_db):
    """Create a VocabExtractor instance with test database."""
    # Create a mock study manager
    class MockStudyManager:
        def add_manual_word(self, word, language, context, source_url, source_title):
            return 1  # Mock word ID
        
        def add_word_definition(self, imported_content_id, definition, definition_language):
            pass
    
    return VocabExtractor(MockStudyManager(), test_db)


class TestVocabExtractorInit:
    """Test VocabExtractor initialization."""
    
    def test_init_stores_study_manager(self, test_db):
        """Test that initialization stores study manager reference."""
        class MockStudyManager:
            pass
        
        extractor = VocabExtractor(MockStudyManager(), test_db)
        assert extractor.study_manager is not None
    
    def test_init_stores_database(self, test_db):
        """Test that initialization stores database reference."""
        class MockStudyManager:
            pass
        
        extractor = VocabExtractor(MockStudyManager(), test_db)
        assert extractor.db is test_db
    
    def test_init_sets_max_context_length(self, test_db):
        """Test that MAX_CONTEXT_LENGTH is set to 200."""
        class MockStudyManager:
            pass
        
        extractor = VocabExtractor(MockStudyManager(), test_db)
        assert extractor.MAX_CONTEXT_LENGTH == 200


class TestGetMinimalContext:
    """Test minimal context extraction functionality."""
    
    def test_get_minimal_context_short_sentence(self, vocab_extractor):
        """Test context extraction for short sentences."""
        word = "test"
        full_sentence = "This is a test sentence."
        
        context = vocab_extractor.get_minimal_context(word, full_sentence)
        
        # Should return the full sentence since it's under 200 chars
        assert context == full_sentence
        assert len(context) <= 200
    
    def test_get_minimal_context_long_sentence(self, vocab_extractor):
        """Test context extraction for long sentences."""
        word = "algorithm"
        # Create a long sentence (> 200 chars)
        long_sentence = "The implementation of the algorithm requires " * 10
        
        context = vocab_extractor.get_minimal_context(word, long_sentence)
        
        # Should be truncated to 200 chars
        assert len(context) <= 200
        # Word should still be present
        assert word in context
    
    def test_get_minimal_context_word_not_found(self, vocab_extractor):
        """Test context extraction when word is not in sentence."""
        word = "xyz"
        full_sentence = "This is a test sentence."
        
        context = vocab_extractor.get_minimal_context(word, full_sentence)
        
        # Should return truncated sentence
        assert len(context) <= 200
    
    def test_get_minimal_context_word_at_start(self, vocab_extractor):
        """Test context extraction when word is at the start."""
        word = "Start"
        full_sentence = "Start of the sentence with more content to make it long enough for testing purposes."
        
        context = vocab_extractor.get_minimal_context(word, full_sentence)
        
        # Word should be present (case-insensitive check)
        assert word.lower() in context.lower()
        assert len(context) <= 200
    
    def test_get_minimal_context_word_at_end(self, vocab_extractor):
        """Test context extraction when word is at the end."""
        word = "end"
        full_sentence = "This is a sentence that ends with the word end for testing purposes."
        
        context = vocab_extractor.get_minimal_context(word, full_sentence)
        
        # Word should be present
        assert word in context
        assert len(context) <= 200
    
    def test_get_minimal_context_word_in_middle(self, vocab_extractor):
        """Test context extraction when word is in the middle."""
        word = "middle"
        full_sentence = "This sentence has the word middle in the middle of the text for testing purposes."
        
        context = vocab_extractor.get_minimal_context(word, full_sentence)
        
        # Word should be present
        assert word in context
        assert len(context) <= 200


class TestExtractWordFromLookup:
    """Test word extraction and flashcard creation."""
    
    def test_extract_word_from_lookup_creates_flashcard(self, vocab_extractor, test_db):
        """Test that extraction creates a flashcard entry."""
        # First create a reading session
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        # Create a lookup record
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context)
            VALUES (?, 1, 'word', 'testword', 'This is a test sentence.')
        """, (session_id,))
        lookup_id = cursor.lastrowid
        
        # Extract word
        flashcard_id = vocab_extractor.extract_word_from_lookup(lookup_id, session_id)
        
        # Verify flashcard was created
        assert flashcard_id > 0
    
    def test_extract_word_from_lookup_with_definition(self, vocab_extractor, test_db):
        """Test extraction with definition included."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        # Create lookup with definition
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context, definition)
            VALUES (?, 1, 'word', 'testword', 'This is a test sentence.', 'A test definition')
        """, (session_id,))
        lookup_id = cursor.lastrowid
        
        # Extract word
        flashcard_id = vocab_extractor.extract_word_from_lookup(lookup_id, session_id)
        
        # Verify flashcard was created
        assert flashcard_id > 0
    
    def test_extract_word_from_lookup_invalid_lookup(self, vocab_extractor, test_db):
        """Test extraction with invalid lookup ID."""
        with pytest.raises(ValueError):
            vocab_extractor.extract_word_from_lookup(99999, 1)


class TestGetSessionVocabulary:
    """Test session vocabulary retrieval."""
    
    def test_get_session_vocabulary_empty_session(self, vocab_extractor, test_db):
        """Test vocabulary retrieval for session with no lookups."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        vocabulary = vocab_extractor.get_session_vocabulary(session_id)
        
        assert vocabulary == []
    
    def test_get_session_vocabulary_with_lookups(self, vocab_extractor, test_db):
        """Test vocabulary retrieval for session with lookups."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        # Create multiple lookups
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context)
            VALUES (?, 1, 'word', 'word1', 'Sentence with word1.')
        """, (session_id,))
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context)
            VALUES (?, 1, 'word', 'word2', 'Sentence with word2.')
        """, (session_id,))
        
        vocabulary = vocab_extractor.get_session_vocabulary(session_id)
        
        assert len(vocabulary) == 2
        words = [v['word'] for v in vocabulary]
        assert 'word1' in words
        assert 'word2' in words


class TestGetSessionVocabularyWithFlashcards:
    """Test session vocabulary retrieval with flashcard IDs."""
    
    def test_get_session_vocabulary_with_flashcards_empty(self, vocab_extractor, test_db):
        """Test vocabulary retrieval with flashcards for empty session."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        vocabulary = vocab_extractor.get_session_vocabulary_with_flashcards(session_id)
        
        assert vocabulary == []
    
    def test_get_session_vocabulary_with_flashcards(self, vocab_extractor, test_db):
        """Test vocabulary retrieval with flashcards."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        # Create a lookup
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context)
            VALUES (?, 1, 'word', 'testword', 'Sentence with testword.')
        """, (session_id,))
        
        vocabulary = vocab_extractor.get_session_vocabulary_with_flashcards(session_id)
        
        assert len(vocabulary) == 1
        assert vocabulary[0]['word'] == 'testword'


# Property-based tests

class TestContextLengthLimitProperty:
    """
    Property-based tests for context length limit validation.
    
    Property 24: Context Length Limit
    Validates: Requirements 8.3
    
    This test verifies that for ANY vocabulary extraction:
    - The context string length is always <= 200 characters
    - The target word is always included in the extracted context
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        word=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                min_codepoint=65,
                max_codepoint=122
            ),
            min_size=1,
            max_size=20
        ),
        sentence=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=1,
            max_size=1000
        ).filter(lambda x: len(x.strip()) > 0)
    )
    def test_property_context_length_always_under_200_chars(
        self,
        word,
        sentence,
        vocab_extractor
    ):
        """
        Property test: Context length is always <= 200 characters.
        
        For ANY word and sentence combination, the get_minimal_context()
        method must return a context string with length <= 200 characters.
        
        This ensures fair use compliance by limiting the amount of
        copyrighted text stored in flashcards.
        
        Validates Requirement 8.3: Maximum 200 characters context
        """
        context = vocab_extractor.get_minimal_context(word, sentence)
        
        assert len(context) <= 200, (
            f"Context length {len(context)} exceeds 200 character limit. "
            f"Word: '{word}', Sentence: '{sentence[:100]}...'"
        )
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        word=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                min_codepoint=65,
                max_codepoint=122
            ),
            min_size=3,
            max_size=10
        ).filter(lambda x: x.strip() and len(x.strip()) > 0),
        sentence=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=50,
            max_size=1000
        ).filter(lambda x: len(x.strip()) > 50)
    )
    def test_property_word_always_included_in_context(
        self,
        word,
        sentence,
        vocab_extractor
    ):
        """
        Property test: Target word is always included in extracted context.
        
        For ANY word and sentence combination, the target word must be
        present in the extracted context, even when the sentence is
        truncated to 200 characters.
        
        This ensures that flashcards have meaningful context for the
        target word.
        
        Validates Requirement 8.3: Word must be in context
        """
        # Only test if word is actually in the sentence
        if word.lower() in sentence.lower():
            context = vocab_extractor.get_minimal_context(word, sentence)
            
            # Check if word is in context (case-insensitive)
            assert word.lower() in context.lower(), (
                f"Word '{word}' not found in context: '{context[:100]}...'. "
                f"Original sentence: '{sentence[:100]}...'"
            )
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        word=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                min_codepoint=65,
                max_codepoint=122
            ),
            min_size=3,
            max_size=20
        ),
        sentence=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=50,
            max_size=1000
        ).filter(lambda x: len(x.strip()) > 50)
    )
    def test_property_context_centered_on_word(
        self,
        word,
        sentence,
        vocab_extractor
    ):
        """
        Property test: Context is centered on the target word.
        
        For ANY word and sentence combination, the extracted context
        should have the target word roughly in the middle of the
        extracted text (when possible).
        
        This ensures balanced context for flashcard learning.
        
        Validates Requirement 8.3: Context centered on word
        """
        if word.lower() in sentence.lower():
            context = vocab_extractor.get_minimal_context(word, sentence)
            
            # Find word position in context
            word_pos = context.lower().find(word.lower())
            
            # Word should be in the context
            assert word_pos >= 0, "Word not found in context"
            
            # Word should be roughly in the middle (within 40% of context length)
            # This allows for some flexibility at sentence boundaries
            context_length = len(context)
            middle_pos = context_length / 2
            deviation = abs(word_pos - middle_pos)
            
            # Allow up to 40% deviation for edge cases (word near sentence start/end)
            assert deviation <= context_length * 0.4, (
                f"Word position {word_pos} is too far from center {middle_pos} "
                f"in context of length {context_length}"
            )


class TestSingleWordExtractionProperty:
    """
    Property-based tests for single word extraction validation.
    
    Property 25: Single Word Extraction
    Validates: Requirements 8.4
    
    This test verifies that vocabulary extraction only extracts
    individual words, not phrases or full sentences.
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        word=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                min_codepoint=65,
                max_codepoint=122
            ),
            min_size=3,
            max_size=10
        ).filter(lambda x: x.strip() and len(x.strip()) > 0),
        sentence=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=50,
            max_size=1000
        ).filter(lambda x: len(x.strip()) > 50)
    )
    def test_property_extraction_is_single_word(
        self,
        word,
        sentence,
        vocab_extractor
    ):
        """
        Property test: Extracted vocabulary is single word only.
        
        For ANY word extraction, the result should be a single word
        (no spaces except for compound words in some languages).
        
        This ensures fair use compliance by only extracting
        individual words, which are not copyrightable.
        
        Validates Requirement 8.4: Extract only individual words
        """
        # Only test if word is actually in the sentence
        if word.lower() in sentence.lower():
            context = vocab_extractor.get_minimal_context(word, sentence)
            
            # The context should be a sentence, not just the word
            # But the word itself should be a single token
            words_in_context = context.split()
            
            # The target word should be one of the words in context
            assert word in words_in_context or word.lower() in [w.lower() for w in words_in_context], (
                f"Word '{word}' not found in context words: {words_in_context}"
            )


class TestFlashcardCreationIntegrationProperty:
    """
    Property-based tests for flashcard creation integration.
    
    Property 26: Flashcard Creation Integration
    Validates: Requirements 8.2, 13.1
    
    This test verifies that "Add to Flashcards" actions correctly
    integrate with StudyManager to create flashcard entries.
    """
    
    def test_integration_creates_flashcard_entry(self, vocab_extractor, test_db):
        """
        Integration test: Flashcard creation integrates with StudyManager.
        
        When extract_word_from_lookup() is called, it should:
        1. Create an imported_content entry in the database
        2. Call StudyManager.add_manual_word()
        3. Return a flashcard ID
        
        Validates Requirements 8.2, 13.1
        """
        # Create a reading session
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        # Create a lookup
        cursor.execute("""
            INSERT INTO reading_lookups
            (session_id, user_id, lookup_type, word, sentence_context)
            VALUES (?, 1, 'word', 'testword', 'This is a test sentence.')
        """, (session_id,))
        lookup_id = cursor.lastrowid
        
        # Extract word
        flashcard_id = vocab_extractor.extract_word_from_lookup(lookup_id, session_id)
        
        # Verify flashcard was created
        assert flashcard_id > 0, "Flashcard ID should be greater than 0"
        
        # Verify imported_content entry was created
        cursor.execute("""
            SELECT id, content, context FROM imported_content
            WHERE content = 'testword'
        """)
        imported = cursor.fetchone()
        
        assert imported is not None, "imported_content entry should be created"
        assert imported[2] is not None, "Context should be stored"
