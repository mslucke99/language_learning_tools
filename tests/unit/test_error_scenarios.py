"""
Unit tests for error handling scenarios in Adventure Graded Reader.

Tests error recovery mechanisms including LLM service unavailability,
insufficient vocabulary warnings, database connection loss, and
corrupted session state handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.features.reader.session_manager import StorySessionManager
from src.features.reader.story_generator import StoryGenerator
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
    InsufficientVocabularyError,
    InvalidChoiceError,
    SessionNotFoundError
)
from src.core.database import FlashcardDatabase


class TestErrorScenarios:
    """Test error handling and recovery mechanisms."""
    
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
        service.add_encountered_words = Mock()
        return service
    
    @pytest.fixture
    def mock_story_generator(self):
        """Create a mock story generator."""
        return Mock()
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        return Mock()
    
    @pytest.fixture
    def session_manager(self, mock_database, mock_vocabulary_service, mock_story_generator):
        """Create a StorySessionManager with mocks."""
        return StorySessionManager(
            database=mock_database,
            vocabulary_service=mock_vocabulary_service,
            story_generator=mock_story_generator
        )
    
    @pytest.fixture
    def story_generator_llm(self, mock_database, mock_llm_service):
        """Create a StoryGenerator in LLM mode."""
        return StoryGenerator(
            mode=GenerationMode.LLM,
            database=mock_database,
            llm_service=mock_llm_service
        )
    
    # Test 1: LLM Service Unavailable
    def test_llm_service_unavailable_fallback(self, story_generator_llm, mock_database):
        """
        Error Scenario 1: LLM service is unavailable.
        
        Verifies that when LLM service is unavailable, the system
        automatically falls back to template generation.
        """
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        
        constraints = VocabularyConstraints(
            known_words={"the", "detective", "room", "dark", "entered", "looked", "around", "with", "a", "mysterious", "atmosphere", "ancient", "artifacts", "were", "in", "is", "and", "of"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.90
        )
        
        # Mock LLM agent to raise exception
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM service unavailable")
        )
        
        # Mock template engine to return valid passage
        valid_passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="The detective entered the dark room and looked around with a mysterious atmosphere.",
            new_words=[NewWord("detective", "investigator", "The detective entered the dark room.")],
            choices=[Choice(1, "Look around"), Choice(2, "Call for help")],
            created_at="2024-01-01T00:00:00"
        )
        
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": "mystery", "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage - should fallback
        passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify fallback occurred
        assert passage is not None
        story_generator_llm.template_engine.fill_template.assert_called_once()
    
    # Test 2: Insufficient Vocabulary Warning
    def test_insufficient_vocabulary_warning(self, session_manager, mock_database, mock_vocabulary_service):
        """
        Error Scenario 2: User has insufficient vocabulary.
        
        Verifies that when user vocabulary is below minimum threshold,
        an InsufficientVocabularyError is raised with helpful message.
        """
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
        with pytest.raises(InsufficientVocabularyError) as exc_info:
            session_manager.process_choice(1, 0)
        
        # Verify error message is helpful
        assert "insufficient vocabulary" in str(exc_info.value).lower()
        assert "study more flashcards" in str(exc_info.value).lower()
    
    # Test 3: Database Connection Loss Recovery
    def test_database_connection_loss_recovery(self, session_manager, mock_database):
        """
        Error Scenario 3: Database connection is lost during operation.
        
        Verifies that database connection errors are caught and
        appropriate recovery is attempted.
        """
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        # First call fails, simulating connection loss
        cursor_mock.execute.side_effect = Exception("Database connection lost")
        
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
        
        # Attempt to save session
        result = session_manager.save_session(session)
        
        # Verify error was handled
        assert result is False
        mock_database.conn.rollback.assert_called_once()
    
    # Test 4: Corrupted Session State Detection
    def test_corrupted_session_state_detection(self, session_manager, mock_database):
        """
        Error Scenario 4: Session state in database is corrupted.
        
        Verifies that corrupted session data is detected and
        appropriate error is raised.
        """
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        
        # Return corrupted data (invalid JSON)
        cursor_mock.fetchone.return_value = (
            1, "korean", "mystery", "template", None,
            "INVALID JSON {{{",  # Corrupted context
            json.dumps([]),
            "2024-01-01T00:00:00",
            "2024-01-01T00:00:00"
        )
        
        # Attempt to load session
        with pytest.raises(Exception):  # JSON decode error
            session_manager.load_session(1)
    
    # Test 5: Invalid Choice Error
    def test_invalid_choice_error(self, session_manager, mock_database):
        """
        Error Scenario 5: User selects invalid choice.
        
        Verifies that selecting a choice that doesn't exist
        raises InvalidChoiceError.
        """
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
        
        # First call: load session
        cursor_mock.fetchone.return_value = (
            1, "korean", "mystery", "template", 1,
            context_json, json.dumps([]), "2024-01-01T00:00:00", "2024-01-01T00:00:00"
        )
        
        # Mock passage with specific choices
        passage = StoryPassage(
            id=1,
            session_id=1,
            passage_number=1,
            story_text="Test passage with test word",
            new_words=[NewWord("test", "test", "Test passage with test word")],
            choices=[Choice(1, "Choice 1"), Choice(2, "Choice 2")],
            created_at="2024-01-01T00:00:00"
        )
        
        # Mock _load_passage to return the passage
        with patch.object(session_manager, '_load_passage', return_value=passage):
            # Try to select invalid choice (3 doesn't exist)
            with pytest.raises(InvalidChoiceError) as exc_info:
                session_manager.process_choice(1, 3)
            
            # Verify error message
            assert "not valid" in str(exc_info.value).lower()
    
    # Test 6: LLM Timeout Handling
    def test_llm_timeout_handling(self, story_generator_llm, mock_database):
        """
        Error Scenario 6: LLM request times out.
        
        Verifies that LLM timeouts are caught and fallback
        to template generation occurs.
        """
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        
        constraints = VocabularyConstraints(
            known_words={"the", "detective", "room", "dark", "entered", "looked", "around", "with", "a", "mysterious", "atmosphere", "ancient", "artifacts", "were", "in", "is", "and", "of"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.90
        )
        
        # Mock LLM agent to raise timeout
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=TimeoutError("LLM request timed out after 60 seconds")
        )
        
        # Mock template engine
        valid_passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="The detective entered the room and looked around with a mysterious atmosphere.",
            new_words=[NewWord("detective", "investigator", "The detective entered the room.")],
            choices=[Choice(1, "Look around"), Choice(2, "Call for help")],
            created_at="2024-01-01T00:00:00"
        )
        
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": "mystery", "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage - should fallback
        passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify fallback occurred
        assert passage is not None
        story_generator_llm.template_engine.fill_template.assert_called_once()
    
    # Test 7: Invalid Generation Mode
    def test_invalid_generation_mode_error(self, mock_database, mock_llm_service):
        """
        Error Scenario 7: Invalid generation mode specified.
        
        Verifies that invalid generation modes are rejected.
        """
        with pytest.raises((ValueError, AttributeError)):
            StoryGenerator(
                mode="invalid_mode",  # Invalid mode
                database=mock_database,
                llm_service=mock_llm_service
            )
    
    # Test 8: LLM Mode Without Service
    def test_llm_mode_without_service_error(self, mock_database):
        """
        Error Scenario 8: LLM mode selected but no LLM service provided.
        
        Verifies that LLM mode requires an LLM service.
        """
        with pytest.raises(ValueError, match="llm_service is required"):
            StoryGenerator(
                mode=GenerationMode.LLM,
                database=mock_database,
                llm_service=None  # Missing service
            )
    
    # Test 9: Empty Template Database
    def test_empty_template_database_error(self, story_generator_llm, mock_database):
        """
        Error Scenario 9: No templates available for genre.
        
        Verifies that when no templates exist for a genre,
        appropriate error is raised.
        """
        context = StoryContext(
            genre="unknown_genre",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        
        constraints = VocabularyConstraints(
            known_words={"the", "detective", "room"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        # Mock LLM to fail
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM error")
        )
        
        # Mock template engine to return no templates
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[]
        )
        
        # Generate passage should raise error
        with pytest.raises(ValueError, match="No templates found"):
            story_generator_llm.generate_passage(context, constraints)
    
    # Test 10: Session Not Found
    def test_session_not_found_error(self, session_manager, mock_database):
        """
        Error Scenario 10: Attempt to load non-existent session.
        
        Verifies that loading a non-existent session raises
        SessionNotFoundError.
        """
        cursor_mock = Mock()
        mock_database.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = None
        
        with pytest.raises(SessionNotFoundError):
            session_manager.load_session(999)
