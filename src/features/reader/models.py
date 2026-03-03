"""
Data models for the Adventure Graded Reader feature.

This module defines the core data structures used throughout the reader system,
including story sessions, passages, vocabulary constraints, and validation results.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional
from enum import Enum
import json


class GenerationMode(Enum):
    """Story generation mode."""
    TEMPLATE = "template"
    LLM = "llm"


@dataclass
class NewWord:
    """
    Represents a new vocabulary word introduced in a story passage.
    
    Attributes:
        word: The new vocabulary word in target language
        translation: Translation in native language
        context_sentence: Sentence from passage containing the word
    
    Validation Rules:
        - word must be present in story_text
        - translation must be non-empty
        - context_sentence must contain word
    """
    word: str
    translation: str
    context_sentence: str
    
    def __post_init__(self):
        """Validate NewWord data."""
        if not self.word or not self.word.strip():
            raise ValueError("word must be non-empty")
        if not self.translation or not self.translation.strip():
            raise ValueError("translation must be non-empty")
        if not self.context_sentence or not self.context_sentence.strip():
            raise ValueError("context_sentence must be non-empty")
        if self.word not in self.context_sentence:
            raise ValueError(f"context_sentence must contain word '{self.word}'")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "word": self.word,
            "translation": self.translation,
            "context_sentence": self.context_sentence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NewWord":
        """Create NewWord from dictionary."""
        return cls(
            word=data["word"],
            translation=data["translation"],
            context_sentence=data["context_sentence"]
        )


@dataclass
class Choice:
    """
    Represents a user choice in the story.
    
    Attributes:
        id: Unique identifier for the choice
        text: Choice text in target language
        description: Brief description in native language (optional)
    
    Validation Rules:
        - text must be non-empty
        - text must use known vocabulary + session vocabulary
    """
    id: int
    text: str
    description: str = ""
    
    def __post_init__(self):
        """Validate Choice data."""
        if not self.text or not self.text.strip():
            raise ValueError("text must be non-empty")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Choice":
        """Create Choice from dictionary."""
        return cls(
            id=data["id"],
            text=data["text"],
            description=data.get("description", "")
        )


@dataclass
class StoryPassage:
    """
    Represents a single passage in the story.
    
    Attributes:
        id: Database ID (None for unsaved passages)
        session_id: ID of the story session
        passage_number: Sequential number of this passage
        story_text: The narrative in target language
        new_words: List of 1-2 new vocabulary words
        choices: List of 2-3 choices for user
        created_at: Timestamp of creation
    
    Validation Rules:
        - story_text must be non-empty
        - new_words must contain 1-2 items
        - choices must contain 2-3 items
        - All text must be in target language
    """
    session_id: int
    passage_number: int
    story_text: str
    new_words: List[NewWord]
    choices: List[Choice]
    created_at: str
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate StoryPassage data."""
        if not self.story_text or not self.story_text.strip():
            raise ValueError("story_text must be non-empty")
        if not (1 <= len(self.new_words) <= 2):
            raise ValueError(f"new_words must contain 1-2 items, got {len(self.new_words)}")
        if not (2 <= len(self.choices) <= 3):
            raise ValueError(f"choices must contain 2-3 items, got {len(self.choices)}")
        
        # Validate that new words are present in story text
        for new_word in self.new_words:
            if new_word.word not in self.story_text:
                raise ValueError(f"new word '{new_word.word}' not found in story_text")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "passage_number": self.passage_number,
            "story_text": self.story_text,
            "new_words": json.dumps([w.to_dict() for w in self.new_words]),
            "choices": json.dumps([c.to_dict() for c in self.choices]),
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StoryPassage":
        """Create StoryPassage from database row."""
        new_words_data = json.loads(data["new_words"]) if isinstance(data["new_words"], str) else data["new_words"]
        choices_data = json.loads(data["choices"]) if isinstance(data["choices"], str) else data["choices"]
        
        return cls(
            id=data.get("id"),
            session_id=data["session_id"],
            passage_number=data["passage_number"],
            story_text=data["story_text"],
            new_words=[NewWord.from_dict(w) for w in new_words_data],
            choices=[Choice.from_dict(c) for c in choices_data],
            created_at=data["created_at"]
        )


@dataclass
class StoryContext:
    """
    Represents the current context/state of the story.
    
    Attributes:
        genre: Story genre (mystery, adventure, fantasy, etc.)
        current_location: Current location in the story
        characters: List of characters in the story
        plot_summary: Summary of story so far
        previous_choices: List of choice IDs made by user
        mood: Current story mood/tone
    
    Validation Rules:
        - genre must be from available genres list
        - plot_summary should be concise (< 500 chars)
    """
    genre: str
    current_location: str
    characters: List[str]
    plot_summary: str
    previous_choices: List[int]
    mood: str
    
    def __post_init__(self):
        """Validate StoryContext data."""
        if not self.genre or not self.genre.strip():
            raise ValueError("genre must be non-empty")
        if len(self.plot_summary) > 500:
            raise ValueError(f"plot_summary too long: {len(self.plot_summary)} chars (max 500)")
    
    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps({
            "genre": self.genre,
            "current_location": self.current_location,
            "characters": self.characters,
            "plot_summary": self.plot_summary,
            "previous_choices": self.previous_choices,
            "mood": self.mood
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "StoryContext":
        """Create StoryContext from JSON string."""
        data = json.loads(json_str)
        return cls(
            genre=data["genre"],
            current_location=data["current_location"],
            characters=data["characters"],
            plot_summary=data["plot_summary"],
            previous_choices=data["previous_choices"],
            mood=data["mood"]
        )


@dataclass
class StorySession:
    """
    Represents a story session.
    
    Attributes:
        language: Target language for the story
        genre: Story genre
        generation_mode: 'template' or 'llm'
        story_context: Current story state
        vocabulary_introduced: Words introduced this session
        created_at: Timestamp of creation
        last_updated: Timestamp of last update
        id: Database ID (None for unsaved sessions)
        current_passage_id: ID of current passage
        completed: Whether session is completed
    
    Validation Rules:
        - language must be non-empty string
        - generation_mode must be 'template' or 'llm'
        - story_context must be valid JSON
    """
    language: str
    genre: str
    generation_mode: GenerationMode
    story_context: StoryContext
    vocabulary_introduced: List[str]
    created_at: str
    last_updated: str
    id: Optional[int] = None
    current_passage_id: Optional[int] = None
    completed: int = 0
    
    def __post_init__(self):
        """Validate StorySession data."""
        if not self.language or not self.language.strip():
            raise ValueError("language must be non-empty")
        if not isinstance(self.generation_mode, GenerationMode):
            raise ValueError(f"generation_mode must be GenerationMode enum, got {type(self.generation_mode)}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "language": self.language,
            "genre": self.genre,
            "generation_mode": self.generation_mode.value,
            "current_passage_id": self.current_passage_id,
            "story_context": self.story_context.to_json(),
            "vocabulary_introduced": json.dumps(self.vocabulary_introduced),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "completed": self.completed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StorySession":
        """Create StorySession from database row."""
        vocab_data = data["vocabulary_introduced"]
        if isinstance(vocab_data, str):
            vocab_introduced = json.loads(vocab_data) if vocab_data else []
        else:
            vocab_introduced = vocab_data or []
        
        return cls(
            id=data.get("id"),
            language=data["language"],
            genre=data["genre"],
            generation_mode=GenerationMode(data["generation_mode"]),
            current_passage_id=data.get("current_passage_id"),
            story_context=StoryContext.from_json(data["story_context"]),
            vocabulary_introduced=vocab_introduced,
            created_at=data["created_at"],
            last_updated=data["last_updated"],
            completed=data.get("completed", 0)
        )


@dataclass
class VocabularyConstraints:
    """
    Represents vocabulary constraints for story generation.
    
    Attributes:
        known_words: User's known vocabulary
        session_words: Words introduced this session
        max_new_words: Maximum new words per passage (default 2)
        min_coverage: Minimum % of known words (default 0.95)
    
    Validation Rules:
        - known_words must not be empty
        - max_new_words must be 1-3
        - min_coverage must be 0.90-0.99
    """
    known_words: Set[str]
    session_words: Set[str] = field(default_factory=set)
    max_new_words: int = 2
    min_coverage: float = 0.95
    
    def __post_init__(self):
        """Validate VocabularyConstraints data."""
        if not self.known_words:
            raise ValueError("known_words must not be empty")
        if not (1 <= self.max_new_words <= 3):
            raise ValueError(f"max_new_words must be 1-3, got {self.max_new_words}")
        if not (0.90 <= self.min_coverage <= 0.99):
            raise ValueError(f"min_coverage must be 0.90-0.99, got {self.min_coverage}")


@dataclass
class ValidationResult:
    """
    Represents the result of vocabulary validation.
    
    Attributes:
        is_valid: Whether the passage meets constraints
        coverage: Vocabulary coverage percentage (0.0-1.0)
        unknown_words: List of unknown words found
        message: Optional validation message
    """
    is_valid: bool
    coverage: float
    unknown_words: List[str]
    message: str = ""
    
    def __post_init__(self):
        """Validate ValidationResult data."""
        if not (0.0 <= self.coverage <= 1.0):
            raise ValueError(f"coverage must be 0.0-1.0, got {self.coverage}")
