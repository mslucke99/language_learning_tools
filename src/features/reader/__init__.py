"""
Adventure Graded Reader - Interactive language learning stories.

This package provides a Choose Your Own Adventure interactive fiction engine
that generates stories constrained to the user's known vocabulary, supporting
both template-based (low-cost) and LLM-based (high-quality) generation modes.

Main Components:
- VocabularyService: Manages user's known vocabulary
- StoryGenerator: Generates story passages (template or LLM)
- StorySessionManager: Manages story sessions and state
- TemplateEngine: Template-based story generation
- AdventureReaderAgent: LLM-based story generation
- ReaderCLI: Command-line interface

Usage:
    from src.features.reader import ReaderCLI
    
    cli = ReaderCLI()
    cli.run()
"""

from .models import (
    StorySession,
    StoryPassage,
    StoryContext,
    VocabularyConstraints,
    GenerationMode,
    NewWord,
    Choice,
    ValidationResult
)

from .exceptions import (
    ReaderError,
    LLMGenerationError,
    InvalidChoiceError,
    TemplateNotFoundError,
    InsufficientVocabularyError,
    SessionNotFoundError,
    DatabaseConnectionError,
    CorruptedSessionError,
    ValidationError
)

from .vocabulary_service import VocabularyService
from .story_generator import StoryGenerator
from .session_manager import StorySessionManager
from .template_engine import TemplateEngine, StoryTemplate
from .llm_agent import AdventureReaderAgent
from .validator import VocabularyValidator, validate_vocabulary
from .recovery import SessionRecovery
from .reader_cli import ReaderCLI
from .content_parser import ContentParser


__all__ = [
    # Models
    'StorySession',
    'StoryPassage',
    'StoryContext',
    'VocabularyConstraints',
    'GenerationMode',
    'NewWord',
    'Choice',
    'ValidationResult',
    
    # Exceptions
    'ReaderError',
    'LLMGenerationError',
    'InvalidChoiceError',
    'TemplateNotFoundError',
    'InsufficientVocabularyError',
    'SessionNotFoundError',
    'DatabaseConnectionError',
    'CorruptedSessionError',
    'ValidationError',
    
    # Services
    'VocabularyService',
    'StoryGenerator',
    'StorySessionManager',
    'TemplateEngine',
    'StoryTemplate',
    'AdventureReaderAgent',
    'VocabularyValidator',
    'validate_vocabulary',
    'SessionRecovery',
    'ContentParser',
    
    # CLI
    'ReaderCLI',
]


__version__ = '1.0.0'
