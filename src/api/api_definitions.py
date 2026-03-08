"""
Type definitions for API request/response payloads.

This module provides TypedDict classes for API endpoints, enabling
better type safety in request/response handling.
"""

from typing import TypedDict, Optional, List, Any


# ===== DECK ENDPOINTS =====

class CreateDeckRequestDict(TypedDict, total=False):
    """Request payload for POST /api/decks."""
    name: str
    description: Optional[str]
    language: Optional[str]


class CreateDeckResponseDict(TypedDict):
    """Response payload for POST /api/decks."""
    success: bool
    deck_id: Optional[int]
    name: Optional[str]
    error: Optional[str]


class GetDeckResponseDict(TypedDict, total=False):
    """Response payload for GET /api/decks/<id>."""
    success: bool
    deck: Optional[dict]
    stats: Optional[dict]
    card_count: Optional[int]
    error: Optional[str]


# ===== FLASHCARD ENDPOINTS =====

class AddCardRequestDict(TypedDict, total=False):
    """Request payload for POST /api/decks/<id>/cards."""
    question: str
    answer: str


class AddCardResponseDict(TypedDict):
    """Response payload for POST /api/decks/<id>/cards."""
    success: bool
    card_id: Optional[int]
    message: Optional[str]
    error: Optional[str]


class CardBatchItem(TypedDict):
    """Single card in batch request."""
    question: str
    answer: str


class AddCardsBatchRequestDict(TypedDict):
    """Request payload for POST /api/decks/<id>/cards/batch."""
    cards: List[CardBatchItem]


class AddCardsBatchResponseDict(TypedDict):
    """Response payload for POST /api/decks/<id>/cards/batch."""
    success: bool
    added: int
    failed: int
    cards: Optional[List[dict]]
    error: Optional[str]


class GetCardsResponseDict(TypedDict):
    """Response payload for GET /api/decks/<id>/cards."""
    success: bool
    cards: Optional[List[dict]]
    error: Optional[str]


class DueCardsResponseDict(TypedDict):
    """Response payload for GET /api/decks/<id>/due."""
    success: bool
    due_count: Optional[int]
    cards: Optional[List[dict]]
    error: Optional[str]


class DeckStatsResponseDict(TypedDict):
    """Response payload for GET /api/decks/<id>/stats."""
    success: bool
    stats: Optional[dict]
    error: Optional[str]


# ===== AI ENDPOINTS =====

class DefineWordRequestDict(TypedDict, total=False):
    """Request payload for POST /api/ai/define."""
    word: str
    language: Optional[str]
    explain_in: Optional[str]


class DefineWordResponseDict(TypedDict, total=False):
    """Response payload for POST /api/ai/define."""
    success: bool
    word: Optional[str]
    definition: Optional[str]
    language: Optional[str]
    error: Optional[str]


class ExplainGrammarRequestDict(TypedDict, total=False):
    """Request payload for POST /api/ai/explain."""
    topic: str
    language: Optional[str]
    explain_in: Optional[str]


class ExplainGrammarResponseDict(TypedDict, total=False):
    """Response payload for POST /api/ai/explain."""
    success: bool
    topic: Optional[str]
    explanation: Optional[str]
    language: Optional[str]
    error: Optional[str]


class AIStatusResponseDict(TypedDict):
    """Response payload for GET /api/ai/status."""
    available: bool
    timestamp: str


class ModelsResponseDict(TypedDict):
    """Response payload for GET /api/ai/models."""
    success: bool
    available: bool
    models: Optional[List[str]]
    current_model: Optional[str]
    ai_running: Optional[bool]
    error: Optional[str]


# ===== IMPORTED CONTENT ENDPOINTS =====

class AddImportedContentRequestDict(TypedDict, total=False):
    """Request payload for POST /api/imported."""
    content_type: str  # 'word', 'sentence', 'phrase'
    content: str
    url: str
    title: Optional[str]
    context: Optional[str]
    language: Optional[str]
    tags: Optional[str]


class AddImportedContentResponseDict(TypedDict):
    """Response payload for POST /api/imported."""
    success: bool
    content_id: Optional[int]
    message: Optional[str]
    error: Optional[str]


class GetImportedContentResponseDict(TypedDict):
    """Response payload for GET /api/imported."""
    success: bool
    content: Optional[List[dict]]
    error: Optional[str]


class ImportedStatsResponseDict(TypedDict):
    """Response payload for GET /api/imported/stats."""
    success: bool
    stats: Optional[dict]
    error: Optional[str]


# ===== SENTENCE SCORING ENDPOINTS =====

class ScoreSentencesRequestDict(TypedDict):
    """Request payload for POST /api/sentences/score."""
    sentences: List[str]
    language: str


class SentenceScoreResult(TypedDict):
    """Result item in sentence scoring response."""
    sentence: str
    difficulty_score: float
    confidence: float
    category: str
    bottleneck_word: Optional[str]
    unknown_count: int


class ScoreSentencesResponseDict(TypedDict):
    """Response payload for POST /api/sentences/score."""
    success: bool
    scores: Optional[List[SentenceScoreResult]]
    error: Optional[str]


# ===== EXTENSION HEALTHCHECK =====

class ExtensionPingResponseDict(TypedDict):
    """Response payload for GET /api/extension/ping."""
    status: str
