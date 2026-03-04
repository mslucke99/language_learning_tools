"""
Exception classes for Adventure Graded Reader.

This module defines all custom exceptions used throughout the reader feature,
providing clear error handling and recovery mechanisms.
"""


class ReaderError(Exception):
    """Base exception for all Adventure Graded Reader errors."""
    pass


class LLMGenerationError(ReaderError):
    """
    Exception raised when LLM generation fails.
    
    This error is raised after all retry attempts have been exhausted
    and the LLM service is unable to generate a valid story passage.
    
    Recovery: The system should fall back to template-based generation.
    """
    pass


class InvalidChoiceError(ReaderError):
    """
    Exception raised when an invalid choice is made.
    
    This error occurs when a user selects a choice_id that does not
    exist in the current passage's available choices.
    
    Recovery: Prompt the user to select a valid choice from the list.
    """
    pass


class TemplateNotFoundError(ReaderError):
    """
    Exception raised when no templates are found for a genre.
    
    This error occurs when the template engine cannot find any story
    templates for the requested genre in the database.
    
    Recovery: 
    - Suggest available genres to the user
    - Seed the database with default templates
    - Fall back to a default genre (e.g., "adventure")
    """
    pass


class InsufficientVocabularyError(ReaderError):
    """
    Exception raised when user has insufficient vocabulary for a story.
    
    This error occurs when the user's known vocabulary is too small
    to generate a meaningful story (typically < 50 words).
    
    Recovery:
    - Inform the user they need to learn more vocabulary first
    - Suggest studying flashcards before using the reader
    - Provide a minimum vocabulary threshold message
    """
    pass


class SessionNotFoundError(ReaderError):
    """
    Exception raised when a session is not found in the database.
    
    This error occurs when attempting to load or operate on a session
    that does not exist or has been deleted.
    
    Recovery:
    - Inform the user the session no longer exists
    - Offer to create a new session
    - Display list of available sessions
    """
    pass


class DatabaseConnectionError(ReaderError):
    """
    Exception raised when database connection is lost or unavailable.
    
    This error occurs when the database connection fails during an operation.
    
    Recovery:
    - Attempt to reconnect with exponential backoff
    - Cache session state temporarily
    - Export session to temporary file for recovery
    """
    pass


class CorruptedSessionError(ReaderError):
    """
    Exception raised when session data is corrupted or invalid.
    
    This error occurs when session data cannot be parsed or contains
    invalid JSON, missing required fields, or inconsistent state.
    
    Recovery:
    - Attempt to repair session data if possible
    - Restore from last known good state
    - Offer to delete corrupted session and start fresh
    """
    pass


class ValidationError(ReaderError):
    """
    Exception raised when passage validation fails.
    
    This error occurs when a generated passage does not meet the
    vocabulary constraints (coverage < 95% or wrong number of new words).
    
    Recovery:
    - Retry generation with stricter constraints
    - Fall back to template generation
    - Log validation failure for monitoring
    """
    pass
