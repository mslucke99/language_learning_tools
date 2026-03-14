"""
Story Generator for Adventure Graded Reader.

This module provides the StoryGenerator class that orchestrates story generation
using either template-based or LLM-based approaches, with automatic validation
and fallback mechanisms.
"""

from typing import List, Optional
from dataclasses import dataclass
import logging

from .models import (
    StoryPassage,
    StoryContext,
    VocabularyConstraints,
    ValidationResult,
    GenerationMode
)
from .template_engine import TemplateEngine
from .llm_agent import AdventureReaderAgent
from .validator import validate_vocabulary
from .exceptions import TemplateNotFoundError, InsufficientVocabularyError
from ...services.llm_service import LLMService
from ...core.database import FlashcardDatabase


logger = logging.getLogger(__name__)


class StoryGenerator:
    """
    Orchestrates story generation using template or LLM modes.
    
    Responsibilities:
    - Generate story passages constrained to known vocabulary
    - Validate output meets vocabulary constraints (95% known, 5% new)
    - Support both template and LLM generation modes
    - Provide automatic fallback from LLM to template on failure
    """
    
    def __init__(
        self,
        mode: GenerationMode,
        database: FlashcardDatabase,
        llm_service: Optional[LLMService] = None
    ):
        """
        Initialize the StoryGenerator.
        
        Args:
            mode: Generation mode (TEMPLATE or LLM)
            database: Database instance for template storage
            llm_service: LLM service for high-quality mode (required if mode is LLM)
        
        Raises:
            ValueError: If mode is LLM but llm_service is None
        """
        self.mode = mode
        self.database = database
        
        # Initialize template engine (always available for fallback)
        self.template_engine = TemplateEngine(database)
        
        # Initialize LLM agent if in LLM mode
        if mode == GenerationMode.LLM:
            if llm_service is None:
                raise ValueError("llm_service is required for LLM generation mode")
            self.llm_agent = AdventureReaderAgent(llm_service)
        else:
            self.llm_agent = None
        
        logger.info(f"StoryGenerator initialized in {mode.value} mode")
    
    def generate_passage(
        self,
        context: StoryContext,
        vocabulary: VocabularyConstraints
    ) -> StoryPassage:
        """
        Generate a story passage using the configured mode.
        
        This method orchestrates the generation process, calling either
        the template engine or LLM agent based on the configured mode.
        
        Args:
            context: Current story context (genre, location, characters, etc.)
            vocabulary: Vocabulary constraints (known words, max new words, etc.)
        
        Returns:
            StoryPassage: Generated passage meeting vocabulary constraints
        
        Raises:
            ValueError: If vocabulary constraints are invalid
        """
        logger.debug(f"Generating passage in {self.mode.value} mode for genre: {context.genre}")
        
        # Validate vocabulary constraints
        if not vocabulary.known_words:
            raise ValueError("known_words cannot be empty")
        
        # Generate based on mode
        if self.mode == GenerationMode.TEMPLATE:
            passage = self._generate_from_template(context, vocabulary)
        else:  # GenerationMode.LLM
            passage = self._generate_from_llm(context, vocabulary)
        
        # Validate the generated passage
        validation = self.validate_output(passage, vocabulary)
        
        if not validation.is_valid:
            logger.warning(
                f"Generated passage failed validation: "
                f"coverage={validation.coverage:.2%}, "
                f"unknown_words={len(validation.unknown_words)}"
            )
            # Note: Fallback is handled in _generate_from_llm
            # If we reach here with invalid passage, it's a critical error
            raise ValueError(
                f"Generated passage failed validation: "
                f"coverage={validation.coverage:.2%} (required: {vocabulary.min_coverage:.2%})"
            )
        
        logger.info(
            f"Successfully generated passage: "
            f"coverage={validation.coverage:.2%}, "
            f"new_words={len(passage.new_words)}"
        )
        
        return passage
    
    def _generate_from_template(
        self,
        context: StoryContext,
        vocabulary: VocabularyConstraints
    ) -> StoryPassage:
        """Generate passage using template engine."""
        logger.debug(f"Generating from template for genre: {context.genre}")
        
        # Load templates for the genre
        templates = self.template_engine.load_templates(context.genre)
        
        if not templates:
            raise ValueError(f"No templates found for genre: {context.genre}")
        
        # Determine which template node to use based on previous choices
        if context.previous_choices:
            last_choice = context.previous_choices[-1]
            # Get the next node based on the last choice
            # For now, use a simple approach - this will be enhanced in template_engine
            template = templates[0]  # Use first template for now
        else:
            # Starting a new story - use the first template
            template = templates[0]
        
        # Fill the template with vocabulary
        passage = self.template_engine.fill_template(template, vocabulary)
        
        return passage
    
    def _generate_from_llm(
        self,
        context: StoryContext,
        vocabulary: VocabularyConstraints
    ) -> StoryPassage:
        """
        Generate passage using LLM agent with automatic fallback.
        
        This method attempts LLM generation and automatically falls back
        to template generation if LLM fails after retries.
        
        The LLM agent internally retries 3 times with exponential backoff.
        If all 3 attempts fail, this method catches the exception and
        falls back to template generation.
        
        Returns:
            StoryPassage: Generated passage from LLM or template fallback
        """
        logger.debug(f"Generating from LLM for genre: {context.genre}")
        
        if self.llm_agent is None:
            logger.warning(
                "LLM agent not initialized, falling back to template mode. "
                "This may indicate LLMService was not provided during initialization."
            )
            return self._generate_from_template(context, vocabulary)
        
        try:
            # Attempt LLM generation (includes internal retry logic with 3 attempts)
            logger.info("Attempting LLM generation (up to 3 retries with exponential backoff)")
            passage = self.llm_agent.generate_story_passage(context, vocabulary)
            logger.info("LLM generation succeeded")
            return passage
            
        except Exception as e:
            # LLM generation failed after all 3 retries
            logger.error(
                f"LLM generation failed after 3 attempts: {e}. "
                f"Falling back to template mode for genre '{context.genre}'. "
                f"This fallback ensures story continuity despite LLM unavailability."
            )
            
            # Log fallback event for monitoring
            logger.warning(
                f"FALLBACK EVENT: LLM -> Template | "
                f"Genre: {context.genre} | "
                f"Error: {type(e).__name__}"
            )
            
            # Use template fallback
            return self._generate_from_template(context, vocabulary)
    
    def validate_output(
        self,
        passage: StoryPassage,
        vocabulary: VocabularyConstraints
    ) -> ValidationResult:
        """
        Validate that a passage meets vocabulary constraints.
        
        Args:
            passage: The story passage to validate
            vocabulary: Vocabulary constraints to check against
        
        Returns:
            ValidationResult: Validation result with coverage and unknown words
        """
        return validate_vocabulary(passage, vocabulary)
    
    def get_available_genres(self) -> List[str]:
        """
        Get list of available story genres.
        
        Returns:
            List of genre names available for story generation
        """
        # Query database for unique genres in story_templates table
        cursor = self.database.conn.cursor()
        cursor.execute("SELECT DISTINCT genre FROM story_templates ORDER BY genre")
        genres = [row[0] for row in cursor.fetchall()]
        
        if not genres:
            # Return default genres if no templates in database
            logger.warning("No genres found in database, returning defaults")
            return ["mystery", "adventure", "fantasy"]
        
        return genres
