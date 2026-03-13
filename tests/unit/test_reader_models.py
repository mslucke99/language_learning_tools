"""
Unit tests for Adventure Graded Reader data models.

Tests validation rules, serialization/deserialization, and edge cases
for all data models used in the reader feature.
"""

import pytest
import json
from datetime import datetime

from src.features.reader.models import (
    NewWord,
    Choice,
    StoryPassage,
    StoryContext,
    StorySession,
    VocabularyConstraints,
    ValidationResult,
    GenerationMode,
)


class TestNewWord:
    """Test cases for NewWord model."""
    
    def test_valid_new_word(self):
        """Test creating a valid NewWord."""
        word = NewWord(
            word="학교",
            translation="school",
            context_sentence="나는 학교에 갑니다."
        )
        assert word.word == "학교"
        assert word.translation == "school"
        assert "학교" in word.context_sentence
    
    def test_empty_word_raises_error(self):
        """Test that empty word raises ValueError."""
        with pytest.raises(ValueError, match="word must be non-empty"):
            NewWord(word="", translation="school", context_sentence="test")
    
    def test_empty_translation_raises_error(self):
        """Test that empty translation raises ValueError."""
        with pytest.raises(ValueError, match="translation must be non-empty"):
            NewWord(word="학교", translation="", context_sentence="나는 학교에 갑니다.")
    
    def test_empty_context_raises_error(self):
        """Test that empty context_sentence raises ValueError."""
        with pytest.raises(ValueError, match="context_sentence must be non-empty"):
            NewWord(word="학교", translation="school", context_sentence="")
    
    def test_word_not_in_context_raises_error(self):
        """Test that word must be present in context_sentence."""
        with pytest.raises(ValueError, match="context_sentence must contain word"):
            NewWord(
                word="학교",
                translation="school",
                context_sentence="나는 집에 갑니다."  # doesn't contain 학교
            )
    
    def test_whitespace_only_word_raises_error(self):
        """Test that whitespace-only word raises ValueError."""
        with pytest.raises(ValueError, match="word must be non-empty"):
            NewWord(word="   ", translation="school", context_sentence="test")
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        word = NewWord(
            word="학교",
            translation="school",
            context_sentence="나는 학교에 갑니다."
        )
        data = word.to_dict()
        assert data["word"] == "학교"
        assert data["translation"] == "school"
        assert data["context_sentence"] == "나는 학교에 갑니다."
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "word": "학교",
            "translation": "school",
            "context_sentence": "나는 학교에 갑니다."
        }
        word = NewWord.from_dict(data)
        assert word.word == "학교"
        assert word.translation == "school"
        assert word.context_sentence == "나는 학교에 갑니다."
    
    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserve data."""
        original = NewWord(
            word="도서관",
            translation="library",
            context_sentence="도서관에서 책을 읽습니다."
        )
        data = original.to_dict()
        restored = NewWord.from_dict(data)
        assert restored.word == original.word
        assert restored.translation == original.translation
        assert restored.context_sentence == original.context_sentence


class TestChoice:
    """Test cases for Choice model."""
    
    def test_valid_choice(self):
        """Test creating a valid Choice."""
        choice = Choice(id=1, text="창문 밖을 본다", description="Look out the window")
        assert choice.id == 1
        assert choice.text == "창문 밖을 본다"
        assert choice.description == "Look out the window"
    
    def test_choice_without_description(self):
        """Test creating a Choice without description."""
        choice = Choice(id=1, text="창문 밖을 본다")
        assert choice.description == ""
    
    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="text must be non-empty"):
            Choice(id=1, text="")
    
    def test_whitespace_only_text_raises_error(self):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="text must be non-empty"):
            Choice(id=1, text="   ")
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        choice = Choice(id=1, text="창문 밖을 본다", description="Look out the window")
        data = choice.to_dict()
        assert data["id"] == 1
        assert data["text"] == "창문 밖을 본다"
        assert data["description"] == "Look out the window"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"id": 1, "text": "창문 밖을 본다", "description": "Look out the window"}
        choice = Choice.from_dict(data)
        assert choice.id == 1
        assert choice.text == "창문 밖을 본다"
        assert choice.description == "Look out the window"
    
    def test_from_dict_without_description(self):
        """Test deserialization without description field."""
        data = {"id": 1, "text": "창문 밖을 본다"}
        choice = Choice.from_dict(data)
        assert choice.description == ""


class TestStoryPassage:
    """Test cases for StoryPassage model."""
    
    def test_valid_passage(self):
        """Test creating a valid StoryPassage."""
        new_words = [
            NewWord("어두운", "dark", "방이 어두운 곳입니다."),
        ]
        choices = [
            Choice(1, "창문 밖을 본다"),
            Choice(2, "문을 연다"),
        ]
        passage = StoryPassage(
            session_id=1,
            passage_number=1,
            story_text="방이 어두운 곳입니다.",
            new_words=new_words,
            choices=choices,
            created_at="2024-01-01T00:00:00"
        )
        assert passage.session_id == 1
        assert len(passage.new_words) == 1
        assert len(passage.choices) == 2
    
    def test_empty_story_text_raises_error(self):
        """Test that empty story_text raises ValueError."""
        with pytest.raises(ValueError, match="story_text must be non-empty"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="",
                new_words=[NewWord("test", "test", "test")],
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
    
    def test_zero_new_words_raises_error(self):
        """Test that 0 new words raises ValueError."""
        with pytest.raises(ValueError, match="new_words must contain 1-2 items"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="Test story",
                new_words=[],
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
    
    def test_three_new_words_raises_error(self):
        """Test that 3 new words raises ValueError."""
        new_words = [
            NewWord("word1", "trans1", "word1 context"),
            NewWord("word2", "trans2", "word2 context"),
            NewWord("word3", "trans3", "word3 context"),
        ]
        with pytest.raises(ValueError, match="new_words must contain 1-2 items"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="word1 word2 word3 context",
                new_words=new_words,
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
    
    def test_one_choice_raises_error(self):
        """Test that 1 choice raises ValueError."""
        with pytest.raises(ValueError, match="choices must contain 2-3 items"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="Test story with word",
                new_words=[NewWord("word", "trans", "Test story with word")],
                choices=[Choice(1, "choice1")],
                created_at="2024-01-01T00:00:00"
            )
    
    def test_four_choices_raises_error(self):
        """Test that 4 choices raises ValueError."""
        choices = [
            Choice(1, "choice1"),
            Choice(2, "choice2"),
            Choice(3, "choice3"),
            Choice(4, "choice4"),
        ]
        with pytest.raises(ValueError, match="choices must contain 2-3 items"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="Test story with word",
                new_words=[NewWord("word", "trans", "Test story with word")],
                choices=choices,
                created_at="2024-01-01T00:00:00"
            )
    
    def test_new_word_not_in_text_raises_error(self):
        """Test that new word must be present in story_text."""
        with pytest.raises(ValueError, match="not found in story_text"):
            StoryPassage(
                session_id=1,
                passage_number=1,
                story_text="This is the story",
                new_words=[NewWord("missing", "trans", "missing word")],
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        new_words = [NewWord("word", "trans", "story with word")]
        choices = [Choice(1, "choice1"), Choice(2, "choice2")]
        passage = StoryPassage(
            id=10,
            session_id=1,
            passage_number=1,
            story_text="story with word",
            new_words=new_words,
            choices=choices,
            created_at="2024-01-01T00:00:00"
        )
        data = passage.to_dict()
        assert data["id"] == 10
        assert data["session_id"] == 1
        assert isinstance(data["new_words"], str)  # JSON string
        assert isinstance(data["choices"], str)  # JSON string
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": 10,
            "session_id": 1,
            "passage_number": 1,
            "story_text": "story with word",
            "new_words": json.dumps([{"word": "word", "translation": "trans", "context_sentence": "story with word"}]),
            "choices": json.dumps([{"id": 1, "text": "choice1", "description": ""}, {"id": 2, "text": "choice2", "description": ""}]),
            "created_at": "2024-01-01T00:00:00"
        }
        passage = StoryPassage.from_dict(data)
        assert passage.id == 10
        assert len(passage.new_words) == 1
        assert len(passage.choices) == 2


class TestStoryContext:
    """Test cases for StoryContext model."""
    
    def test_valid_context(self):
        """Test creating a valid StoryContext."""
        context = StoryContext(
            genre="mystery",
            current_location="dark_room",
            characters=["detective", "suspect"],
            plot_summary="A detective investigates a crime.",
            previous_choices=[1, 2],
            mood="tense"
        )
        assert context.genre == "mystery"
        assert len(context.characters) == 2
        assert len(context.previous_choices) == 2
    
    def test_empty_genre_raises_error(self):
        """Test that empty genre raises ValueError."""
        with pytest.raises(ValueError, match="genre must be non-empty"):
            StoryContext(
                genre="",
                current_location="room",
                characters=[],
                plot_summary="test",
                previous_choices=[],
                mood="neutral"
            )
    
    def test_long_plot_summary_raises_error(self):
        """Test that plot_summary > 500 chars raises ValueError."""
        long_summary = "x" * 501
        with pytest.raises(ValueError, match="plot_summary too long"):
            StoryContext(
                genre="mystery",
                current_location="room",
                characters=[],
                plot_summary=long_summary,
                previous_choices=[],
                mood="neutral"
            )
    
    def test_to_json(self):
        """Test serialization to JSON."""
        context = StoryContext(
            genre="mystery",
            current_location="dark_room",
            characters=["detective"],
            plot_summary="A detective investigates.",
            previous_choices=[1, 2],
            mood="tense"
        )
        json_str = context.to_json()
        data = json.loads(json_str)
        assert data["genre"] == "mystery"
        assert data["current_location"] == "dark_room"
        assert len(data["characters"]) == 1
    
    def test_from_json(self):
        """Test deserialization from JSON."""
        json_str = json.dumps({
            "genre": "mystery",
            "current_location": "dark_room",
            "characters": ["detective"],
            "plot_summary": "A detective investigates.",
            "previous_choices": [1, 2],
            "mood": "tense"
        })
        context = StoryContext.from_json(json_str)
        assert context.genre == "mystery"
        assert context.current_location == "dark_room"
        assert len(context.characters) == 1
    
    def test_round_trip_json_serialization(self):
        """Test that JSON serialization preserves data."""
        original = StoryContext(
            genre="adventure",
            current_location="forest",
            characters=["hero", "guide"],
            plot_summary="The hero begins a journey.",
            previous_choices=[1, 3, 2],
            mood="hopeful"
        )
        json_str = original.to_json()
        restored = StoryContext.from_json(json_str)
        assert restored.genre == original.genre
        assert restored.current_location == original.current_location
        assert restored.characters == original.characters
        assert restored.plot_summary == original.plot_summary
        assert restored.previous_choices == original.previous_choices
        assert restored.mood == original.mood


class TestStorySession:
    """Test cases for StorySession model."""
    
    def test_valid_session(self):
        """Test creating a valid StorySession."""
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        session = StorySession(
            language="korean",
            genre="mystery",
            generation_mode=GenerationMode.TEMPLATE,
            story_context=context,
            vocabulary_introduced=["word1", "word2"],
            created_at="2024-01-01T00:00:00",
            last_updated="2024-01-01T00:00:00"
        )
        assert session.language == "korean"
        assert session.generation_mode == GenerationMode.TEMPLATE
        assert len(session.vocabulary_introduced) == 2
    
    def test_empty_language_raises_error(self):
        """Test that empty language raises ValueError."""
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        with pytest.raises(ValueError, match="language must be non-empty"):
            StorySession(
                language="",
                genre="mystery",
                generation_mode=GenerationMode.TEMPLATE,
                story_context=context,
                vocabulary_introduced=[],
                created_at="2024-01-01T00:00:00",
                last_updated="2024-01-01T00:00:00"
            )
    
    def test_invalid_generation_mode_raises_error(self):
        """Test that invalid generation_mode raises ValueError."""
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        with pytest.raises(ValueError, match="generation_mode must be GenerationMode enum"):
            StorySession(
                language="korean",
                genre="mystery",
                generation_mode="invalid",  # Should be GenerationMode enum
                story_context=context,
                vocabulary_introduced=[],
                created_at="2024-01-01T00:00:00",
                last_updated="2024-01-01T00:00:00"
            )
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        context = StoryContext(
            genre="mystery",
            current_location="room",
            characters=[],
            plot_summary="Start",
            previous_choices=[],
            mood="neutral"
        )
        session = StorySession(
            id=1,
            language="korean",
            genre="mystery",
            generation_mode=GenerationMode.LLM,
            story_context=context,
            vocabulary_introduced=["word1"],
            created_at="2024-01-01T00:00:00",
            last_updated="2024-01-01T00:00:00"
        )
        data = session.to_dict()
        assert data["id"] == 1
        assert data["language"] == "korean"
        assert data["generation_mode"] == "llm"
        assert isinstance(data["story_context"], str)
        assert isinstance(data["vocabulary_introduced"], str)
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        context_json = json.dumps({
            "genre": "mystery",
            "current_location": "room",
            "characters": [],
            "plot_summary": "Start",
            "previous_choices": [],
            "mood": "neutral"
        })
        data = {
            "id": 1,
            "language": "korean",
            "genre": "mystery",
            "generation_mode": "template",
            "current_passage_id": None,
            "story_context": context_json,
            "vocabulary_introduced": json.dumps(["word1"]),
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "completed": 0
        }
        session = StorySession.from_dict(data)
        assert session.id == 1
        assert session.language == "korean"
        assert session.generation_mode == GenerationMode.TEMPLATE
        assert len(session.vocabulary_introduced) == 1


class TestVocabularyConstraints:
    """Test cases for VocabularyConstraints model."""
    
    def test_valid_constraints(self):
        """Test creating valid VocabularyConstraints."""
        constraints = VocabularyConstraints(
            known_words={"word1", "word2", "word3"},
            session_words={"word4"},
            max_new_words=2,
            min_coverage=0.95
        )
        assert len(constraints.known_words) == 3
        assert len(constraints.session_words) == 1
        assert constraints.max_new_words == 2
        assert constraints.min_coverage == 0.95
    
    def test_empty_known_words_raises_error(self):
        """Test that empty known_words raises ValueError."""
        with pytest.raises(ValueError, match="known_words must not be empty"):
            VocabularyConstraints(known_words=set())
    
    def test_max_new_words_too_low_raises_error(self):
        """Test that max_new_words < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_new_words must be 1-3"):
            VocabularyConstraints(
                known_words={"word1"},
                max_new_words=0
            )
    
    def test_max_new_words_too_high_raises_error(self):
        """Test that max_new_words > 3 raises ValueError."""
        with pytest.raises(ValueError, match="max_new_words must be 1-3"):
            VocabularyConstraints(
                known_words={"word1"},
                max_new_words=4
            )
    
    def test_min_coverage_too_low_raises_error(self):
        """Test that min_coverage < 0.90 raises ValueError."""
        with pytest.raises(ValueError, match="min_coverage must be 0.90-0.99"):
            VocabularyConstraints(
                known_words={"word1"},
                min_coverage=0.89
            )
    
    def test_min_coverage_too_high_raises_error(self):
        """Test that min_coverage > 0.99 raises ValueError."""
        with pytest.raises(ValueError, match="min_coverage must be 0.90-0.99"):
            VocabularyConstraints(
                known_words={"word1"},
                min_coverage=1.0
            )
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        constraints = VocabularyConstraints(known_words={"word1"})
        assert constraints.session_words == set()
        assert constraints.max_new_words == 2
        assert constraints.min_coverage == 0.95


class TestValidationResult:
    """Test cases for ValidationResult model."""
    
    def test_valid_result(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            coverage=0.95,
            unknown_words=["word1", "word2"],
            message="Validation passed"
        )
        assert result.is_valid is True
        assert result.coverage == 0.95
        assert len(result.unknown_words) == 2
    
    def test_coverage_below_zero_raises_error(self):
        """Test that coverage < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="coverage must be 0.0-1.0"):
            ValidationResult(
                is_valid=False,
                coverage=-0.1,
                unknown_words=[]
            )
    
    def test_coverage_above_one_raises_error(self):
        """Test that coverage > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="coverage must be 0.0-1.0"):
            ValidationResult(
                is_valid=False,
                coverage=1.1,
                unknown_words=[]
            )
    
    def test_boundary_coverage_values(self):
        """Test that boundary values 0.0 and 1.0 are valid."""
        result1 = ValidationResult(is_valid=True, coverage=0.0, unknown_words=[])
        result2 = ValidationResult(is_valid=True, coverage=1.0, unknown_words=[])
        assert result1.coverage == 0.0
        assert result2.coverage == 1.0
    
    def test_default_message(self):
        """Test that default message is empty string."""
        result = ValidationResult(is_valid=True, coverage=0.95, unknown_words=[])
        assert result.message == ""


class TestGenerationMode:
    """Test cases for GenerationMode enum."""
    
    def test_template_mode(self):
        """Test TEMPLATE mode value."""
        assert GenerationMode.TEMPLATE.value == "template"
    
    def test_llm_mode(self):
        """Test LLM mode value."""
        assert GenerationMode.LLM.value == "llm"
    
    def test_from_string(self):
        """Test creating GenerationMode from string."""
        mode1 = GenerationMode("template")
        mode2 = GenerationMode("llm")
        assert mode1 == GenerationMode.TEMPLATE
        assert mode2 == GenerationMode.LLM
