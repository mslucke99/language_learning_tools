"""
Story Session Manager for Adventure Graded Reader.

This module manages story sessions, coordinates between components,
and handles save/resume functionality for interactive stories.
"""

from typing import List, Optional
import json
import logging
from datetime import datetime

from .models import (
    StorySession,
    StoryPassage,
    StoryContext,
    VocabularyConstraints,
    GenerationMode,
    NewWord,
    Choice
)
from .vocabulary_service import VocabularyService
from .story_generator import StoryGenerator
from .exceptions import (
    InvalidChoiceError,
    SessionNotFoundError,
    InsufficientVocabularyError,
    TemplateNotFoundError
)
from ...core.database import FlashcardDatabase


logger = logging.getLogger(__name__)


# Note: Exception classes are now imported from exceptions.py


class StorySessionManager:
    """
    Manages story sessions and coordinates story generation.
    
    Responsibilities:
    - Create and manage story sessions
    - Coordinate vocabulary service and story generator
    - Persist story state to database
    - Track story progression and choices made
    - Manage session lifecycle (create, save, resume, delete)
    """
    
    def __init__(
        self,
        database: FlashcardDatabase,
        vocabulary_service: VocabularyService,
        story_generator: StoryGenerator
    ):
        """
        Initialize the StorySessionManager.
        
        Args:
            database: Database instance for persistence
            vocabulary_service: Service for vocabulary management
            story_generator: Generator for story passages
        """
        self.database = database
        self.vocabulary_service = vocabulary_service
        self.story_generator = story_generator
        
        logger.info("StorySessionManager initialized")
    
    def create_session(
        self,
        language: str,
        genre: str,
        generation_mode: GenerationMode
    ) -> int:
        """
        Create a new story session.
        
        Args:
            language: Target language for the story
            genre: Story genre (mystery, adventure, fantasy, etc.)
            generation_mode: Generation mode (TEMPLATE or LLM)
        
        Returns:
            int: The ID of the newly created session
        
        Raises:
            ValueError: If language or genre is empty
        
        Preconditions:
            - language is non-empty string
            - genre is non-empty string
            - Database connection is active
        
        Postconditions:
            - New session is created in database
            - Session ID is returned
            - Initial story context is created
        """
        if not language or not language.strip():
            raise ValueError("language cannot be empty")
        
        if not genre or not genre.strip():
            raise ValueError("genre cannot be empty")
        
        logger.info(f"Creating new session: language={language}, genre={genre}, mode={generation_mode.value}")
        
        # Create initial story context
        initial_context = StoryContext(
            genre=genre,
            current_location="start",
            characters=[],
            plot_summary="The story begins...",
            previous_choices=[],
            mood="mysterious"
        )
        
        # Serialize context to JSON
        context_json = initial_context.to_json()
        
        # Get current timestamp
        now = datetime.now().isoformat()
        
        # Insert into database
        cursor = self.database.conn.cursor()
        cursor.execute("""
            INSERT INTO story_sessions (
                language,
                genre,
                generation_mode,
                current_passage_id,
                story_context,
                vocabulary_introduced,
                created_at,
                last_updated,
                completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            language,
            genre,
            generation_mode.value,
            None,  # No passages yet
            context_json,
            json.dumps([]),  # Empty vocabulary list
            now,
            now,
            0  # Not completed
        ))
        
        self.database.conn.commit()
        session_id = cursor.lastrowid
        
        logger.info(f"Created session {session_id}")
        
        return session_id
    
    def load_session(self, session_id: int) -> StorySession:
        """
        Load an existing story session from the database.
        
        Args:
            session_id: ID of the session to load
        
        Returns:
            StorySession: The loaded session
        
        Raises:
            SessionNotFoundError: If session does not exist
        
        Preconditions:
            - session_id > 0
            - Database connection is active
        
        Postconditions:
            - Returns valid StorySession object
            - Session data matches database state
        """
        if session_id <= 0:
            raise ValueError("session_id must be positive")
        
        logger.debug(f"Loading session {session_id}")
        
        cursor = self.database.conn.cursor()
        cursor.execute("""
            SELECT
                id,
                language,
                genre,
                generation_mode,
                current_passage_id,
                story_context,
                vocabulary_introduced,
                created_at,
                last_updated
            FROM story_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        # Parse vocabulary_introduced JSON
        vocab_json = row[6] or "[]"
        vocabulary_introduced = json.loads(vocab_json)
        
        # Create StorySession object
        session = StorySession(
            id=row[0],
            language=row[1],
            genre=row[2],
            generation_mode=GenerationMode(row[3]),
            current_passage_id=row[4],
            story_context=StoryContext.from_json(row[5]),
            vocabulary_introduced=vocabulary_introduced,
            created_at=row[7],
            last_updated=row[8]
        )
        
        logger.info(f"Loaded session {session_id}: {len(vocabulary_introduced)} words introduced")
        
        return session
    
    def save_session(self, session: StorySession) -> bool:
        """
        Save a story session to the database.
        
        Args:
            session: The session to save
        
        Returns:
            bool: True if save succeeded, False otherwise
        
        Preconditions:
            - session is valid StorySession object
            - session.id exists in database
            - Database connection is active
        
        Postconditions:
            - Session data is persisted to database
            - last_updated timestamp is updated
            - Returns True on success
        """
        if not session or not session.id:
            logger.error("Cannot save session: invalid session or missing ID")
            return False
        
        logger.debug(f"Saving session {session.id}")
        
        try:
            # Update last_updated timestamp
            now = datetime.now().isoformat()
            
            # Serialize vocabulary_introduced
            vocab_json = json.dumps(session.vocabulary_introduced)
            
            cursor = self.database.conn.cursor()
            cursor.execute("""
                UPDATE story_sessions
                SET
                    story_context = ?,
                    vocabulary_introduced = ?,
                    current_passage_id = ?,
                    last_updated = ?
                WHERE id = ?
            """, (
                session.story_context,
                vocab_json,
                session.current_passage_id,
                now,
                session.id
            ))
            
            self.database.conn.commit()
            
            logger.info(f"Saved session {session.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.id}: {e}")
            self.database.conn.rollback()
            return False
    
    def delete_session(self, session_id: int) -> bool:
        """
        Delete a story session and all associated passages.
        
        Args:
            session_id: ID of the session to delete
        
        Returns:
            bool: True if deletion succeeded, False otherwise
        
        Preconditions:
            - session_id > 0
            - Database connection is active
        
        Postconditions:
            - Session is removed from database
            - All associated passages are removed (CASCADE)
            - Returns True on success
        """
        if session_id <= 0:
            raise ValueError("session_id must be positive")
        
        logger.info(f"Deleting session {session_id}")
        
        try:
            cursor = self.database.conn.cursor()
            
            # Delete session (CASCADE will delete passages)
            cursor.execute("""
                DELETE FROM story_sessions
                WHERE id = ?
            """, (session_id,))
            
            deleted_count = cursor.rowcount
            self.database.conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Deleted session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            self.database.conn.rollback()
            return False

    
    def process_choice(
        self,
        session_id: int,
        choice_id: int
    ) -> StoryPassage:
        """
        Process a user's choice and generate the next story passage.
        
        This is the main orchestration method that coordinates all components
        to generate a new passage based on the user's choice.
        
        Args:
            session_id: ID of the story session
            choice_id: ID of the choice made (0 for first passage)
        
        Returns:
            StoryPassage: The newly generated passage
        
        Raises:
            SessionNotFoundError: If session does not exist
            InvalidChoiceError: If choice_id is invalid
            ValueError: If generation fails
        
        Preconditions:
            - session_id exists in database
            - choice_id is valid choice from previous passage (or 0 for first)
            - Database connection is available
        
        Postconditions:
            - New passage is generated and saved
            - Session state is updated with new vocabulary
            - Passage meets vocabulary constraints
            - All new words are tracked in session
        """
        logger.info(f"Processing choice {choice_id} for session {session_id}")
        
        # Step 1: Load session state
        session = self.load_session(session_id)
        
        # Step 2: Get story context (already a StoryContext object from load_session)
        context = session.story_context
        
        # Step 3: Update context based on choice
        if choice_id > 0:
            # Validate that choice exists in current passage
            if session.current_passage_id:
                current_passage = self._load_passage(session.current_passage_id)
                valid_choice_ids = [c.id for c in current_passage.choices]
                
                if choice_id not in valid_choice_ids:
                    raise InvalidChoiceError(
                        f"Choice {choice_id} is not valid for current passage. "
                        f"Valid choices: {valid_choice_ids}"
                    )
            
            # Update context with the choice
            context.previous_choices.append(choice_id)
            # Update plot summary (simplified for now)
            context.plot_summary += f" User chose option {choice_id}."
        
        # Step 4: Get vocabulary constraints
        known_words = set(self.vocabulary_service.get_known_words(session.language))
        session_words = set(session.vocabulary_introduced)
        
        # Check for insufficient vocabulary
        min_required_words = 50
        total_vocab = len(known_words) + len(session_words)
        if total_vocab < min_required_words:
            raise InsufficientVocabularyError(
                f"Insufficient vocabulary for story generation. "
                f"You have {total_vocab} words, but at least {min_required_words} are required. "
                f"Please study more flashcards before using the reader."
            )
        
        constraints = VocabularyConstraints(
            known_words=known_words,
            session_words=session_words,
            max_new_words=2,
            min_coverage=0.95
        )
        
        logger.debug(
            f"Vocabulary: {len(known_words)} known, "
            f"{len(session_words)} session words"
        )
        
        # Step 5: Generate new passage
        try:
            # Sync generator mode with session mode
            self.story_generator.mode = session.generation_mode
            passage = self.story_generator.generate_passage(context, constraints)
        except Exception as e:
            logger.error(f"Failed to generate passage: {e}")
            raise ValueError(f"Story generation failed: {e}")
        
        # Step 6: Determine passage number
        passage_number = self._get_next_passage_number(session_id)
        passage.session_id = session_id
        passage.passage_number = passage_number
        
        # Step 7: Save passage to database
        passage_id = self._save_passage(passage)
        
        # Step 8: Update session with new words
        for new_word in passage.new_words:
            if new_word.word not in session.vocabulary_introduced:
                session.vocabulary_introduced.append(new_word.word)
        
        # Step 9: Update session context and current passage
        session.story_context = context.to_json()
        session.current_passage_id = passage_id
        
        # Step 10: Save updated session
        if not self.save_session(session):
            logger.error("Failed to save session after generating passage")
            # Note: Passage is already saved, so we don't rollback
        
        # Step 11: Track encountered words in vocabulary service
        new_words_data = [
            {"word": nw.word, "translation": nw.translation}
            for nw in passage.new_words
        ]
        self.vocabulary_service.add_encountered_words(session_id, new_words_data)
        
        logger.info(
            f"Generated passage {passage_number} for session {session_id}: "
            f"{len(passage.new_words)} new words, {len(passage.choices)} choices"
        )
        
        return passage
    
    def get_session_history(self, session_id: int) -> List[StoryPassage]:
        """
        Get the complete history of passages for a session.
        
        Args:
            session_id: ID of the session
        
        Returns:
            List[StoryPassage]: List of passages in chronological order
        
        Preconditions:
            - session_id exists in database
            - Database connection is active
        
        Postconditions:
            - Returns passages in chronological order by passage_number
            - All passages belong to the specified session
        """
        logger.debug(f"Loading history for session {session_id}")
        
        cursor = self.database.conn.cursor()
        cursor.execute("""
            SELECT
                id,
                session_id,
                passage_number,
                story_text,
                new_words,
                choices,
                created_at
            FROM story_passages
            WHERE session_id = ?
            ORDER BY passage_number ASC
        """, (session_id,))
        
        rows = cursor.fetchall()
        
        passages = []
        for row in rows:
            # Parse JSON fields
            new_words_json = json.loads(row[4])
            choices_json = json.loads(row[5])
            
            # Convert to objects
            new_words = [
                NewWord(
                    word=nw["word"],
                    translation=nw["translation"],
                    context_sentence=nw["context_sentence"]
                )
                for nw in new_words_json
            ]
            
            choices = [
                Choice(
                    id=c["id"],
                    text=c["text"],
                    description=c.get("description", "")
                )
                for c in choices_json
            ]
            
            passage = StoryPassage(
                id=row[0],
                session_id=row[1],
                passage_number=row[2],
                story_text=row[3],
                new_words=new_words,
                choices=choices,
                created_at=row[6]
            )
            
            passages.append(passage)
        
        logger.info(f"Loaded {len(passages)} passages for session {session_id}")
        
        return passages
    
    def _load_passage(self, passage_id: int) -> StoryPassage:
        """Load a single passage by ID."""
        cursor = self.database.conn.cursor()
        cursor.execute("""
            SELECT
                id,
                session_id,
                passage_number,
                story_text,
                new_words,
                choices,
                created_at
            FROM story_passages
            WHERE id = ?
        """, (passage_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Passage {passage_id} not found")
        
        # Parse JSON fields
        new_words_json = json.loads(row[4])
        choices_json = json.loads(row[5])
        
        new_words = [
            NewWord(
                word=nw["word"],
                translation=nw["translation"],
                context_sentence=nw["context_sentence"]
            )
            for nw in new_words_json
        ]
        
        choices = [
            Choice(
                id=c["id"],
                text=c["text"],
                description=c.get("description", "")
            )
            for c in choices_json
        ]
        
        return StoryPassage(
            id=row[0],
            session_id=row[1],
            passage_number=row[2],
            story_text=row[3],
            new_words=new_words,
            choices=choices,
            created_at=row[6]
        )
    
    def _save_passage(self, passage: StoryPassage) -> int:
        """Save a passage to the database and return its ID."""
        # Serialize new_words and choices to JSON
        new_words_json = json.dumps([
            {
                "word": nw.word,
                "translation": nw.translation,
                "context_sentence": nw.context_sentence
            }
            for nw in passage.new_words
        ])
        
        choices_json = json.dumps([
            {
                "id": c.id,
                "text": c.text,
                "description": c.description
            }
            for c in passage.choices
        ])
        
        cursor = self.database.conn.cursor()
        cursor.execute("""
            INSERT INTO story_passages (
                session_id,
                passage_number,
                story_text,
                new_words,
                choices,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            passage.session_id,
            passage.passage_number,
            passage.story_text,
            new_words_json,
            choices_json,
            passage.created_at
        ))
        
        self.database.conn.commit()
        return cursor.lastrowid
    
    def _get_next_passage_number(self, session_id: int) -> int:
        """Get the next passage number for a session."""
        cursor = self.database.conn.cursor()
        cursor.execute("""
            SELECT MAX(passage_number)
            FROM story_passages
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        max_number = row[0] if row[0] is not None else 0
        
        return max_number + 1
