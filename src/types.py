"""
Shared type definitions for the Language Learning Suite.

This module provides TypedDict classes for common data structures used
throughout the application, enabling better type safety and IDE support.
"""

from typing import TypedDict, Optional, List, Any, Union


class DeckDict(TypedDict, total=False):
    """Typed dictionary for deck data."""
    id: int
    name: str
    description: Optional[str]
    language: Optional[str]
    created_at: str


class FlashcardDict(TypedDict, total=False):
    """Typed dictionary for flashcard data."""
    id: int
    deck_id: int
    question: str
    answer: str
    last_reviewed: Optional[str]
    easiness: float
    interval: int
    repetitions: int
    total_reviews: int
    correct_reviews: int
    accuracy: Optional[float]
    reviews: Optional[int]


class ImportedContentDict(TypedDict, total=False):
    """Typed dictionary for imported content (from browser extension)."""
    id: int
    content_type: str  # 'word', 'sentence', 'phrase'
    content: str
    context: Optional[str]
    title: Optional[str]
    url: str
    language: Optional[str]
    created_at: str
    processed: int  # 0=not processed, 1=processed
    tags: Optional[str]


class WordDefinitionDict(TypedDict, total=False):
    """Typed dictionary for word definitions."""
    id: int
    imported_content_id: int
    word: str
    definition: str
    definition_language: Optional[str]
    source: str  # 'user' or 'ollama'
    created_at: str
    last_updated: str
    examples: Optional[str]  # JSON list
    notes: Optional[str]
    difficulty_level: int


class SentenceExplanationDict(TypedDict, total=False):
    """Typed dictionary for sentence explanations."""
    id: int
    imported_content_id: int
    sentence: str
    explanation: str
    explanation_language: Optional[str]
    source: str  # 'user' or 'ollama'
    focus_area: Optional[str]  # 'grammar', 'vocabulary', 'context', 'all'
    created_at: str
    last_updated: str
    grammar_notes: Optional[str]
    user_notes: Optional[str]


class ChatSessionDict(TypedDict, total=False):
    """Typed dictionary for chat session data."""
    id: int
    topic: str
    language: Optional[str]
    mode: str  # 'topical', 'roleplay', 'freeform'
    cur_topic: Optional[str]
    created_at: str
    last_accessed: Optional[str]


class ChatMessageDict(TypedDict, total=False):
    """Typed dictionary for chat messages."""
    id: int
    session_id: int
    role: str  # 'user', 'assistant'
    content: str
    analysis: Optional[str]  # JSON analysis data
    timestamp: str


class DeckStatisticsDict(TypedDict, total=False):
    """Typed dictionary for deck statistics."""
    total_cards: int
    due_count: int
    reviewed: int
    avg_easiness: float
    avg_interval: float
    learning_efficiency: float


class APIResponseDict(TypedDict, total=False):
    """Typed dictionary for API responses."""
    success: bool
    message: Optional[str]
    error: Optional[str]
    data: Optional[Any]
    timestamp: Optional[str]


class AIDefinitionResponseDict(TypedDict, total=False):
    """Typed dictionary for AI definition API responses."""
    success: bool
    word: str
    definition: str
    language: str
    error: Optional[str]


class SentenceDifficultyResultDict(TypedDict, total=False):
    """Typed dictionary for sentence difficulty scoring results."""
    sentence: str
    difficulty_score: float
    confidence: float
    category: str  # 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'
    bottleneck_word: Optional[str]
    unknown_count: int


class StudySessionDict(TypedDict, total=False):
    """Typed dictionary for study session data."""
    session_id: int
    deck_id: int
    current_card_index: int
    cards_reviewed: int
    correct_count: int
    start_time: str
    end_time: Optional[str]
    accuracy: Optional[float]
