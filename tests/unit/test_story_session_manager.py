"""
Unit tests for StorySessionManager.

Tests session creation, loading, saving, deletion, and choice processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.features.reader.session_manager import StorySessionManager
from src.features.reader.models import (
    GenerationMode,
    StoryContext,
    StorySession,
    StoryPassage,
    NewWord,
    Choice,
    VocabularyConstraints
)
from src.features.reader.exceptions import (
    SessionNotFoundError,
    InvalidChoiceError,
    InsufficientVocabularyError
)
from src.core.database import FlashcardDatabase


class TestStorySessionManager:
    """Test cases for StorySessionManager."""
    
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
        # Return enough words to pass the minimum vocabulary check (50 words)
        known_words = [f"word{i}" for i in range(60)]
        service.get_known_words = Mock(return_value=known_words)
        service.add_encountered_words = Mock()
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
    
    def test_create_session_success(self, session_manager, mock_database):
        """Test successful session creation."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.lastrowid = 1
        
        session_id = session_manager.create_session(
            language="korean",
            genre="mystery",
            generation_mode=GenerationMode.TEMPLATE
        )
        
        assert session_id == 1
        cursor_mock.execute.assert_called_once()
        mock_database.conn.commit.assert_called_once()
    
    def test_create_session_empty_language_raises_error(self, session_manager):
        """Test that empty language raises ValueError."""
        with pytest.raises(ValueError, match="language cannot be empty"):
            session_manager.create_session(
                language="",
                genre="mystery",
                generation_mode=GenerationMode.TEMPLATE
            )
    
    def test_create_session_empty_genre_raises_error(self, session_manager):
        """Test that empty genre raises ValueError."""
        with pytest.raises(ValueError, match="genre cannot be empty"):
            session_manager.create_session(
                language="korean",
                genre="",
                generation_mode=GenerationMode.TEMPLATE
            )
    
    def test_create_session_whitespace_language_raises_error(self, session_manager):
        """Test that whitespace-only language raises ValueError."""
        with pytest.raises(ValueError, match="language cannot be empty"):
            session_manager.create_session(
                language="   ",
                genre="mystery",
                generation_mode=GenerationMode.TEMPLATE
            )
    
    def test_load_session_success(self, session_manager, mock_database):
        """Test successful session loading."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        context_json = json.dumps({
            "genre": "mystery",
            "current_location": "room",
            "characters": [],
            "plot_summary": "Start",
            "previous_choices": [],
            "mood": "neutral"
        })
        
        cursor_mock.fetchone.return_value = (
            1,  # id
            "korean",  # language
            "mystery",  # genre
            "template",  # generation_mode
            None,  # current_passage_id
            context_json,  # story_context
            json.dumps(["word1", "word2"]),  # vocabulary_introduced
            "2024-01-01T00:00:00",  # created_at
            "2024-01-01T12:00:00"  # last_updated
        )
        
        session = session_manager.load_session(1)
        
        assert session.id == 1
        assert session.language == "korean"
        assert session.genre == "mystery"
        assert len(session.vocabulary_introduced) == 2
    
    def test_load_session_not_found_raises_error(self, session_manager, mock_database):
        """Test that loading non-existent session raises SessionNotFoundError."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = None
        
        with pytest.raises(SessionNotFoundError):
            session_manager.load_session(999)
    
    def test_load_session_invalid_id_raises_error(self, session_manager):
        """Test that invalid session ID raises ValueError."""
        with pytest.raises(ValueError, match="session_id must be positive"):
            session_manager.load_session(0)
        
        with pytest.raises(ValueError, match="session_id must be positive"):
            session_manager.load_session(-1)
    
    def test_save_session_success(self, session_manager, mock_database):
        """Test successful session saving."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        session = StorySession(
            id=1,
            language="korean",
            genre="mystery",
            generation_mode=GenerationMode.TEMPLATE,
            story_context=StoryContext(
                genre="mystery",
                current_location="room",
                characters=[],
                plot_summary="Start",
                previous_choices=[],
                mood="neutral"
            ),
            vocabulary_introduced=["word1"],
            created_at="2024-01-01T00:00:00",
            last_updated="2024-01-01T00:00:00"
        )
        
        result = session_manager.save_session(session)
        
        assert result is True
        cursor_mock.execute.assert_called_once()
        mock_database.conn.commit.assert_called_once()
    
    def test_save_session_invalid_session_returns_false(self, session_manager):
        """Test that saving invalid session returns False."""
        result = session_manager.save_session(None)
        assert result is False
    
    def test_save_session_database_error_returns_false(self, session_manager, mock_database):
        """Test that database error during save returns False."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.execute.side_effect = Exception("Database error")
        
        session = StorySession(
            id=1,
            language="korean",
            genre="mystery",
            generation_mode=GenerationMode.TEMPLATE,
            story_context=StoryContext(
                genre="mystery",
                current_location="room",
                characters=[],
                plot_summary="Start",
                previous_choices=[],
                mood="neutral"
            ),
            vocabulary_introduced=[],
            created_at="2024-01-01T00:00:00",
            last_updated="2024-01-01T00:00:00"
        )
        
        result = session_manager.save_session(session)
        
        assert result is False
        mock_database.conn.rollback.assert_called_once()
    
    def test_delete_session_success(self, session_manager, mock_database):
        """Test successful session deletion."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.rowcount = 1
        
        result = session_manager.delete_session(1)
        
        assert result is True
        cursor_mock.execute.assert_called_once()
        mock_database.conn.commit.assert_called_once()
    
    def test_delete_session_not_found_returns_false(self, session_manager, mock_database):
        """Test that deleting non-existent session returns False."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.rowcount = 0
        
        result = session_manager.delete_session(999)
        
        assert result is False
    
    def test_delete_session_invalid_id_raises_error(self, session_manager):
        """Test that invalid session ID raises ValueError."""
        with pytest.raises(ValueError, match="session_id must be positive"):
            session_manager.delete_session(0)
    
    def test_delete_session_database_error_returns_false(self, session_manager, mock_database):
        """Test that database error during delete returns False."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.execute.side_effect = Exception("Database error")
        
        result = session_manager.delete_session(1)
        
        assert result is False
        mock_database.conn.rollback.assert_called_once()
    
    def test_process_choice_first_passage(self, session_manager, mock_database, mock_vocabulary_service, mock_story_generator):
        """Test processing first choice (choice_id=0)."""
        # Setup mocks
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.lastrowid = 1
        
        context_json = json.dumps({
            "genre": "mystery",
            "current_location": "start",
            "characters": [],
            "plot_summary": "Start",
            "previous_choices": [],
            "mood": "neutral"
        })
        
        cursor_mock.fetchone.return_value = (
            1, "korean", "mystery", "template", None,
            context_json, json.dumps([]), "2024-01-01T00:00:00", "2024-01-01T00:00:00"
        )
        
        # Mock story generator
        passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="The detective entered the room.",
            new_words=[NewWord("detective", "investigator", "The detective entered the room.")],
            choices=[Choice(1, "Look around"), Choice(2, "Call for help")],
            created_at="2024-01-01T00:00:00"
        )
        mock_story_generator.generate_passage.return_value = passage
        
        # Process choice
        result = session_manager.process_choice(1, 0)
        
        assert result is not None
        assert isinstance(result, StoryPassage)
        mock_story_generator.generate_passage.assert_called_once()
    
    def test_process_choice_insufficient_vocabulary_raises_error(self, session_manager, mock_database, mock_vocabulary_service):
        """Test that insufficient vocabulary raises InsufficientVocabularyError."""
        # Setup mocks
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        context_json = json.dumps({
            "genre": "mystery",
            "current_location": "start",
            "characters": [],
            "plot_summary": "Start",
            "previous_choices": [],
            "mood": "neutral"
        })
        
        cursor_mock.fetchone.return_value = (
            1, "korean", "mystery", "template", None,
            context_json, json.dumps([]), "2024-01-01T00:00:00", "2024-01-01T00:00:00"
        )
        
        # Mock vocabulary service to return insufficient words
        mock_vocabulary_service.get_known_words.return_value = ["word1", "word2"]
        
        # Process choice should raise error
        with pytest.raises(InsufficientVocabularyError):
            session_manager.process_choice(1, 0)
    
    def test_get_session_history_success(self, session_manager, mock_database):
        """Test successful retrieval of session history."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        # Mock passages with new words that are in the story text
        cursor_mock.fetchall.return_value = [
            (
                1, 1, 1, "First passage with word1 in it",
                json.dumps([{"word": "word1", "translation": "trans1", "context_sentence": "First passage with word1 in it"}]),
                json.dumps([{"id": 1, "text": "Choice 1", "description": ""}, {"id": 2, "text": "Choice 2", "description": ""}]),
                "2024-01-01T00:00:00"
            ),
            (
                2, 1, 2, "Second passage with word2 in it",
                json.dumps([{"word": "word2", "translation": "trans2", "context_sentence": "Second passage with word2 in it"}]),
                json.dumps([{"id": 1, "text": "Choice 1", "description": ""}, {"id": 2, "text": "Choice 2", "description": ""}]),
                "2024-01-01T01:00:00"
            )
        ]
        
        passages = session_manager.get_session_history(1)
        
        assert len(passages) == 2
        assert passages[0].passage_number == 1
        assert passages[1].passage_number == 2
    
    def test_get_session_history_empty(self, session_manager, mock_database):
        """Test retrieval of empty session history."""
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchall.return_value = []
        
        passages = session_manager.get_session_history(1)
        
        assert len(passages) == 0
