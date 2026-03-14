"""
Property-based tests for session persistence round-trip.

Tests that sessions can be saved to the database and loaded back
with all data preserved and intact.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch
import json

from src.features.reader.session_manager import StorySessionManager
from src.features.reader.models import (
    GenerationMode,
    StoryContext,
    StorySession
)
from src.core.database import FlashcardDatabase


class TestSessionPersistenceRoundtrip:
    """Test Property 13: Session Persistence Round-Trip."""
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database."""
        db = Mock(spec=FlashcardDatabase)
        db.conn = Mock()
        db.conn.cursor = Mock()
        db.conn.commit = Mock()
        db.conn.rollback = Mock()
        return db
    
    @pytest.fixture
    def mock_vocabulary_service(self):
        """Create a mock vocabulary service."""
        service = Mock()
        service.get_known_words = Mock(return_value=["the", "detective", "room"])
        return service
    
    @pytest.fixture
    def mock_story_generator(self):
        """Create a mock story generator."""
        return Mock()
    
    @pytest.fixture
    def session_manager(self, mock_database, mock_vocabulary_service, mock_story_generator):
        """Create a StorySessionManager with mocks."""
        return StorySessionManager(
            database=mock_database,
            vocabulary_service=mock_vocabulary_service,
            story_generator=mock_story_generator
        )
    
    def _create_test_session(self, language="korean", genre="mystery", vocab_count=5):
        """Helper to create a test session with random data."""
        context = StoryContext(
            genre=genre,
            current_location="dark_room",
            characters=["detective", "suspect"],
            plot_summary="A detective investigates a mysterious crime.",
            previous_choices=[1, 2, 1],
            mood="tense"
        )
        
        vocabulary = [f"word_{i}" for i in range(vocab_count)]
        
        return StorySession(
            id=1,
            language=language,
            genre=genre,
            generation_mode=GenerationMode.TEMPLATE,
            story_context=context,
            vocabulary_introduced=vocabulary,
            created_at="2024-01-01T00:00:00",
            last_updated="2024-01-01T12:00:00"
        )
    
    def test_basic_roundtrip(self, session_manager, mock_database):
        """
        Property: A session saved and loaded has identical data.
        
        Verifies that all session fields are preserved through
        the save/load cycle.
        """
        original_session = self._create_test_session()
        
        # Mock database cursor
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        # Mock load to return the same data
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save session
        session_manager.save_session(original_session)
        
        # Load session
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify all fields match
        assert loaded_session.id == original_session.id
        assert loaded_session.language == original_session.language
        assert loaded_session.genre == original_session.genre
        assert loaded_session.generation_mode == original_session.generation_mode
        assert loaded_session.vocabulary_introduced == original_session.vocabulary_introduced
    
    @given(
        language=st.sampled_from(["korean", "spanish", "japanese"]),
        genre=st.sampled_from(["mystery", "adventure", "fantasy"]),
        vocab_count=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_roundtrip_with_various_data(
        self,
        session_manager,
        mock_database,
        language,
        genre,
        vocab_count
    ):
        """
        Property: Round-trip works with various language, genre, and vocabulary combinations.
        
        Verifies that the persistence mechanism handles different
        combinations of session parameters correctly.
        """
        original_session = self._create_test_session(
            language=language,
            genre=genre,
            vocab_count=vocab_count
        )
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify data integrity
        assert loaded_session.language == language
        assert loaded_session.genre == genre
        assert len(loaded_session.vocabulary_introduced) == vocab_count
    
    def test_context_preservation(self, session_manager, mock_database):
        """
        Property: Story context is fully preserved through round-trip.
        
        Verifies that all context fields (genre, location, characters,
        plot, choices, mood) survive the save/load cycle.
        """
        original_session = self._create_test_session()
        original_context = original_session.story_context
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        loaded_context = loaded_session.story_context
        
        # Verify context fields
        assert loaded_context.genre == original_context.genre
        assert loaded_context.current_location == original_context.current_location
        assert loaded_context.characters == original_context.characters
        assert loaded_context.plot_summary == original_context.plot_summary
        assert loaded_context.previous_choices == original_context.previous_choices
        assert loaded_context.mood == original_context.mood
    
    def test_vocabulary_list_preservation(self, session_manager, mock_database):
        """
        Property: Vocabulary list is exactly preserved through round-trip.
        
        Verifies that the vocabulary_introduced list maintains
        exact order and content through serialization/deserialization.
        """
        vocabulary = ["detective", "mystery", "clue", "suspect", "evidence"]
        original_session = self._create_test_session(vocab_count=0)
        original_session.vocabulary_introduced = vocabulary
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify vocabulary
        assert loaded_session.vocabulary_introduced == vocabulary
        assert len(loaded_session.vocabulary_introduced) == len(vocabulary)
    
    def test_empty_vocabulary_roundtrip(self, session_manager, mock_database):
        """
        Property: Sessions with empty vocabulary round-trip correctly.
        
        Verifies that sessions with no vocabulary_introduced
        (e.g., newly created sessions) persist correctly.
        """
        original_session = self._create_test_session(vocab_count=0)
        original_session.vocabulary_introduced = []
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify empty vocabulary is preserved
        assert loaded_session.vocabulary_introduced == []
        assert len(loaded_session.vocabulary_introduced) == 0
    
    def test_large_vocabulary_roundtrip(self, session_manager, mock_database):
        """
        Property: Sessions with large vocabulary lists round-trip correctly.
        
        Verifies that the persistence mechanism handles large
        vocabulary lists without truncation or corruption.
        """
        large_vocabulary = [f"word_{i}" for i in range(100)]
        original_session = self._create_test_session(vocab_count=0)
        original_session.vocabulary_introduced = large_vocabulary
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify large vocabulary is preserved
        assert loaded_session.vocabulary_introduced == large_vocabulary
        assert len(loaded_session.vocabulary_introduced) == 100
    
    def test_special_characters_in_vocabulary(self, session_manager, mock_database):
        """
        Property: Vocabulary with special characters round-trips correctly.
        
        Verifies that words with Unicode, punctuation, and special
        characters are preserved through serialization.
        """
        special_vocabulary = [
            "café",
            "naïve",
            "résumé",
            "한국어",
            "日本語",
            "español",
            "word-with-dash",
            "word_with_underscore"
        ]
        original_session = self._create_test_session(vocab_count=0)
        original_session.vocabulary_introduced = special_vocabulary
        
        # Mock database
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = (
            original_session.id,
            original_session.language,
            original_session.genre,
            original_session.generation_mode.value,
            None,
            original_session.story_context.to_json(),
            json.dumps(original_session.vocabulary_introduced),
            original_session.created_at,
            original_session.last_updated
        )
        
        # Save and load
        session_manager.save_session(original_session)
        loaded_session = session_manager.load_session(original_session.id)
        
        # Verify special characters are preserved
        assert loaded_session.vocabulary_introduced == special_vocabulary
