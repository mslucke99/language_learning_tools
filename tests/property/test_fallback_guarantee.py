"""
Property-based tests for StoryGenerator fallback guarantee.

Tests that the template fallback mechanism always produces valid passages
when LLM generation fails, ensuring story continuity despite LLM unavailability.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import logging

from src.features.reader.story_generator import StoryGenerator
from src.features.reader.models import (
    GenerationMode,
    StoryContext,
    VocabularyConstraints,
    StoryPassage,
    NewWord,
    Choice
)
from src.core.database import FlashcardDatabase


logger = logging.getLogger(__name__)


class TestFallbackGuarantee:
    """Test Property 7: Template Fallback Guarantee."""
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database for testing."""
        db = Mock(spec=FlashcardDatabase)
        db.conn = Mock()
        db.conn.cursor = Mock()
        return db
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        return Mock()
    
    @pytest.fixture
    def story_generator_llm(self, mock_database, mock_llm_service):
        """Create a StoryGenerator in LLM mode."""
        return StoryGenerator(
            mode=GenerationMode.LLM,
            database=mock_database,
            llm_service=mock_llm_service
        )
    
    @pytest.fixture
    def story_generator_template(self, mock_database):
        """Create a StoryGenerator in template mode."""
        return StoryGenerator(
            mode=GenerationMode.TEMPLATE,
            database=mock_database
        )
    
    def _create_valid_passage(self):
        """Helper to create a valid test passage."""
        return StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="The detective entered the dark room.",
            new_words=[NewWord("detective", "investigator", "The detective entered the dark room.")],
            choices=[
                Choice(1, "Look around carefully"),
                Choice(2, "Call for backup")
            ],
            created_at="2024-01-01T00:00:00"
        )
    
    def _create_valid_context(self):
        """Helper to create a valid story context."""
        return StoryContext(
            genre="mystery",
            current_location="dark_room",
            characters=["detective"],
            plot_summary="A detective investigates a crime.",
            previous_choices=[],
            mood="tense"
        )
    
    def _create_valid_constraints(self):
        """Helper to create valid vocabulary constraints."""
        return VocabularyConstraints(
            known_words={"the", "detective", "entered", "dark", "room", "looked", "around", "with", "a", "mysterious", "atmosphere", "ancient", "artifacts", "were", "in", "is", "and", "of"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.90
        )
    
    @given(
        failure_count=st.integers(min_value=1, max_value=5),
        genre=st.sampled_from(["mystery", "adventure", "fantasy"])
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_fallback_on_llm_failure(self, story_generator_llm, failure_count, genre):
        """
        Property: When LLM generation fails, fallback to template always succeeds.
        
        This test simulates LLM failures and verifies that the fallback mechanism
        produces a valid passage using the template engine.
        """
        context = self._create_valid_context()
        context.genre = genre
        constraints = self._create_valid_constraints()
        
        # Mock LLM agent to raise an exception
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM service unavailable")
        )
        
        # Mock template engine to return a valid passage
        valid_passage = self._create_valid_passage()
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": genre, "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage - should fallback to template
        passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify fallback occurred
        assert passage is not None
        assert isinstance(passage, StoryPassage)
        assert len(passage.new_words) >= 1
        assert len(passage.choices) >= 2
        
        # Verify template engine was called (fallback)
        story_generator_llm.template_engine.fill_template.assert_called_once()
    
    @given(
        genre=st.sampled_from(["mystery", "adventure", "fantasy"]),
        num_choices=st.integers(min_value=2, max_value=3)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_fallback_produces_valid_passage(self, story_generator_llm, genre, num_choices):
        """
        Property: Fallback passages always meet vocabulary constraints.
        
        Verifies that passages generated via fallback satisfy:
        - 1-2 new words
        - 2-3 choices
        - Non-empty story text
        """
        context = self._create_valid_context()
        context.genre = genre
        constraints = self._create_valid_constraints()
        
        # Mock LLM to fail
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM timeout")
        )
        
        # Create a valid fallback passage with words from constraints
        new_words = [
            NewWord("mysterious", "mysterious", "The detective entered the dark room with a mysterious atmosphere."),
            NewWord("ancient", "ancient", "The ancient artifacts were in the room.")
        ]
        choices = [Choice(i, f"Choice {i}") for i in range(1, num_choices + 1)]
        
        fallback_passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="The detective entered the dark room with a mysterious atmosphere. The ancient artifacts were in the room.",
            new_words=new_words[:2],  # Limit to 2
            choices=choices,
            created_at="2024-01-01T00:00:00"
        )
        
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": genre, "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=fallback_passage
        )
        
        # Generate passage
        passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify passage meets constraints
        assert 1 <= len(passage.new_words) <= 2, "Must have 1-2 new words"
        assert 2 <= len(passage.choices) <= 3, "Must have 2-3 choices"
        assert len(passage.story_text) > 0, "Story text must not be empty"
    
    def test_fallback_preserves_context(self, story_generator_llm):
        """
        Property: Fallback passages preserve story context.
        
        Verifies that context information (genre, location, characters, etc.)
        is maintained when falling back to template generation.
        """
        context = self._create_valid_context()
        original_genre = context.genre
        original_location = context.current_location
        original_characters = context.characters.copy()
        
        constraints = self._create_valid_constraints()
        
        # Mock LLM to fail
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM error")
        )
        
        # Mock template engine
        valid_passage = self._create_valid_passage()
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": original_genre, "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage
        passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify context was preserved
        assert context.genre == original_genre
        assert context.current_location == original_location
        assert context.characters == original_characters
    
    def test_fallback_logging(self, story_generator_llm, caplog):
        """
        Property: Fallback events are logged for monitoring.
        
        Verifies that when fallback occurs, appropriate log messages
        are generated for debugging and monitoring purposes.
        """
        context = self._create_valid_context()
        constraints = self._create_valid_constraints()
        
        # Mock LLM to fail
        story_generator_llm.llm_agent.generate_story_passage = Mock(
            side_effect=Exception("LLM service error")
        )
        
        # Mock template engine
        valid_passage = self._create_valid_passage()
        story_generator_llm.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": "mystery", "template": "test"}]
        )
        story_generator_llm.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage with logging capture
        with caplog.at_level(logging.WARNING):
            passage = story_generator_llm.generate_passage(context, constraints)
        
        # Verify fallback was logged
        assert any("FALLBACK EVENT" in record.message for record in caplog.records)
        assert any("LLM -> Template" in record.message for record in caplog.records)
    
    def test_template_mode_no_fallback_needed(self, story_generator_template):
        """
        Property: Template mode doesn't need fallback.
        
        Verifies that when using template mode directly, no fallback
        mechanism is triggered (no LLM agent exists).
        """
        context = self._create_valid_context()
        constraints = self._create_valid_constraints()
        
        # Verify no LLM agent in template mode
        assert story_generator_template.llm_agent is None
        
        # Mock template engine
        valid_passage = self._create_valid_passage()
        story_generator_template.template_engine.load_templates = Mock(
            return_value=[{"id": 1, "genre": "mystery", "template": "test"}]
        )
        story_generator_template.template_engine.fill_template = Mock(
            return_value=valid_passage
        )
        
        # Generate passage
        passage = story_generator_template.generate_passage(context, constraints)
        
        # Verify passage was generated
        assert passage is not None
        assert isinstance(passage, StoryPassage)
