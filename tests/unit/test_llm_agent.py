"""
Unit tests for AdventureReaderAgent.

Tests prompt building, JSON parsing, retry logic, and timeout handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from src.features.reader.llm_agent import AdventureReaderAgent
from src.features.reader.models import StoryContext, VocabularyConstraints, GenerationMode
from src.features.reader.exceptions import LLMGenerationError


class TestAdventureReaderAgent:
    """Test cases for AdventureReaderAgent"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service"""
        service = Mock()
        service.is_available.return_value = True
        return service
    
    @pytest.fixture
    def agent(self, mock_llm_service):
        """Create an AdventureReaderAgent with mock service"""
        return AdventureReaderAgent(mock_llm_service)
    
    @pytest.fixture
    def sample_context(self):
        """Create a sample story context"""
        return StoryContext(
            genre="mystery",
            current_location="dark_room",
            characters=["detective", "suspect"],
            plot_summary="A detective investigates a crime.",
            previous_choices=[],
            mood="tense"
        )
    
    @pytest.fixture
    def sample_constraints(self):
        """Create sample vocabulary constraints"""
        return VocabularyConstraints(
            known_words={"the", "a", "is", "was", "detective", "room", "dark", "you", "enter", "with", "atmosphere", "of", "and", "in", "to", "object"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.90
        )
    
    def test_build_prompt_includes_known_words(self, agent, sample_context, sample_constraints):
        """Test that prompt includes known words as JSON"""
        prompt = agent.build_prompt(sample_context, sample_constraints)
        
        assert "Known Vocabulary" in prompt
        assert "detective" in prompt
        assert "mystery" in prompt
    
    def test_build_prompt_includes_context(self, agent, sample_context, sample_constraints):
        """Test that prompt includes story context"""
        prompt = agent.build_prompt(sample_context, sample_constraints)
        
        assert "dark_room" in prompt
        assert "detective" in prompt
        assert "A detective investigates a crime." in prompt
    
    def test_build_prompt_includes_constraints(self, agent, sample_context, sample_constraints):
        """Test that prompt includes vocabulary constraints"""
        prompt = agent.build_prompt(sample_context, sample_constraints)
        
        assert "95%" in prompt or "0.95" in prompt
        assert "vocabulary" in prompt.lower()
    
    def test_build_prompt_output_format(self, agent, sample_context, sample_constraints):
        """Test that prompt specifies JSON output format"""
        prompt = agent.build_prompt(sample_context, sample_constraints)
        
        assert "JSON" in prompt
        assert "story_text" in prompt
        assert "new_words" in prompt
        assert "choices" in prompt
    
    def test_parse_response_valid_json(self, agent):
        """Test parsing valid JSON response"""
        response = json.dumps({
            "story_text": "You enter a mysterious dark room with ancient artifacts.",
            "new_words": [
                {"word": "mysterious", "translation": "mysterious", "context_sentence": "You enter a mysterious dark room."},
                {"word": "ancient", "translation": "ancient", "context_sentence": "The ancient artifacts are everywhere."}
            ],
            "choices": [
                {"id": 1, "text": "Examine the room", "description": "Look around"},
                {"id": 2, "text": "Leave", "description": "Exit the room"}
            ]
        })
        
        passage = agent.parse_response(response)
        
        assert passage.story_text == "You enter a mysterious dark room with ancient artifacts."
        assert len(passage.new_words) == 2
        assert len(passage.choices) == 2
    
    def test_parse_response_with_extra_text(self, agent):
        """Test parsing response with extra text around JSON"""
        response = """
        Here's the story:
        
        {
            "story_text": "You enter a mysterious dark room.",
            "new_words": [
                {"word": "mysterious", "translation": "mysterious", "context_sentence": "You enter a mysterious dark room."}
            ],
            "choices": [
                {"id": 1, "text": "Examine", "description": "Look"},
                {"id": 2, "text": "Leave", "description": "Exit"}
            ]
        }
        
        That's the story!
        """
        
        passage = agent.parse_response(response)
        
        assert passage.story_text == "You enter a mysterious dark room."
        assert len(passage.new_words) == 1
    
    def test_parse_response_invalid_json(self, agent):
        """Test parsing invalid JSON raises error"""
        response = "This is not JSON at all"
        
        with pytest.raises(json.JSONDecodeError):
            agent.parse_response(response)
    
    def test_parse_response_missing_story_text(self, agent):
        """Test parsing response missing story_text"""
        response = json.dumps({
            "new_words": [],
            "choices": [{"id": 1, "text": "choice"}]
        })
        
        with pytest.raises(ValueError, match="story_text is required"):
            agent.parse_response(response)
    
    def test_parse_response_malformed_new_words(self, agent):
        """Test parsing response with malformed new_words"""
        response = json.dumps({
            "story_text": "Story",
            "new_words": "not a list",
            "choices": [{"id": 1, "text": "choice"}]
        })
        
        with pytest.raises(ValueError, match="new_words must be a list"):
            agent.parse_response(response)
    
    def test_parse_response_ensures_minimum_choices(self, agent):
        """Test that parsed response has at least 2 choices"""
        response = json.dumps({
            "story_text": "This is a test story.",
            "new_words": [{"word": "test", "translation": "test", "context_sentence": "This is a test story."}],
            "choices": [{"id": 1, "text": "choice"}]
        })
        
        passage = agent.parse_response(response)
        
        # Should have at least 2 choices (fallback added)
        assert len(passage.choices) >= 2
    
    def test_parse_response_limits_new_words(self, agent):
        """Test that parsed response limits new words to 2"""
        response = json.dumps({
            "story_text": "Story with test1 test2 test3",
            "new_words": [
                {"word": "test1", "translation": "test1", "context_sentence": "Story with test1 test2 test3"},
                {"word": "test2", "translation": "test2", "context_sentence": "Story with test1 test2 test3"},
                {"word": "test3", "translation": "test3", "context_sentence": "Story with test1 test2 test3"}
            ],
            "choices": [{"id": 1, "text": "choice1"}, {"id": 2, "text": "choice2"}]
        })
        
        passage = agent.parse_response(response)
        
        # Should limit to 2 new words
        assert len(passage.new_words) <= 2
    
    def test_generate_story_passage_success(self, agent, sample_context, sample_constraints, mock_llm_service):
        """Test successful story passage generation"""
        # Use a simpler story text with mostly known words
        mock_llm_service.generate_response.return_value = json.dumps({
            "story_text": "You enter a dark room. A mysterious object is in the room.",
            "new_words": [
                {"word": "mysterious", "translation": "mysterious", "context_sentence": "A mysterious object is in the room."}
            ],
            "choices": [
                {"id": 1, "text": "Examine", "description": "Look"},
                {"id": 2, "text": "Leave", "description": "Exit"}
            ]
        })
        
        passage = agent.generate_story_passage(sample_context, sample_constraints)
        
        assert passage is not None
        assert "mysterious" in passage.story_text
    
    def test_generate_story_passage_retry_on_failure(self, agent, sample_context, sample_constraints, mock_llm_service):
        """Test retry logic on LLM failure"""
        # First two calls fail, third succeeds
        response = json.dumps({
            "story_text": "You enter a dark room. A mysterious object is in the room.",
            "new_words": [
                {"word": "mysterious", "translation": "mysterious", "context_sentence": "A mysterious object is in the room."}
            ],
            "choices": [
                {"id": 1, "text": "Examine", "description": "Look"},
                {"id": 2, "text": "Leave", "description": "Exit"}
            ]
        })
        
        mock_llm_service.generate_response.side_effect = [
            None,  # First call returns None
            None,  # Second call returns None
            response  # Third call succeeds
        ]
        
        passage = agent.generate_story_passage(sample_context, sample_constraints, max_retries=3)
        
        assert passage is not None
        assert mock_llm_service.generate_response.call_count == 3
    
    def test_generate_story_passage_max_retries_exceeded(self, agent, sample_context, sample_constraints, mock_llm_service):
        """Test that LLMGenerationError is raised after max retries"""
        mock_llm_service.generate_response.side_effect = Exception("LLM service error")
        
        with pytest.raises(LLMGenerationError):
            agent.generate_story_passage(sample_context, sample_constraints, max_retries=2)
    
    def test_is_available(self, agent, mock_llm_service):
        """Test checking if LLM service is available"""
        mock_llm_service.is_available.return_value = True
        
        assert agent.is_available() is True
        
        mock_llm_service.is_available.return_value = False
        
        assert agent.is_available() is False
