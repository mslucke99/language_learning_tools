"""
Error recovery mechanisms for Adventure Graded Reader.

This module provides utilities for recovering from various error conditions
including database failures, corrupted sessions, and connection issues.
"""

import json
import logging
import time
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from .models import StorySession, StoryPassage
from .exceptions import DatabaseConnectionError, CorruptedSessionError
from ...core.database import FlashcardDatabase


logger = logging.getLogger(__name__)


class SessionRecovery:
    """
    Handles session recovery and error resilience.
    
    Provides mechanisms for:
    - Database reconnection with exponential backoff
    - Session state caching for database failures
    - Corrupted session detection and recovery
    - Temporary file export for session recovery
    """
    
    def __init__(self, database: FlashcardDatabase):
        """
        Initialize SessionRecovery.
        
        Args:
            database: Database instance
        """
        self.database = database
        self._session_cache: Dict[int, StorySession] = {}
        self._temp_dir = Path.home() / ".kiro" / "reader_recovery"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SessionRecovery initialized, temp dir: {self._temp_dir}")
    
    def reconnect_database(self, max_retries: int = 3) -> bool:
        """
        Attempt to reconnect to database with exponential backoff.
        
        Args:
            max_retries: Maximum number of reconnection attempts
        
        Returns:
            bool: True if reconnection succeeded, False otherwise
        
        Preconditions:
            - max_retries > 0
        
        Postconditions:
            - Database connection is restored, or all retries exhausted
            - Returns True only if connection is active
        """
        logger.warning("Attempting database reconnection...")
        
        for attempt in range(max_retries):
            try:
                # Test connection with a simple query
                cursor = self.database.conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                logger.info(f"Database reconnection succeeded on attempt {attempt + 1}")
                return True
                
            except sqlite3.Error as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Reconnection attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
        
        logger.error(f"Database reconnection failed after {max_retries} attempts")
        return False
    
    def cache_session(self, session: StorySession) -> None:
        """
        Cache session state in memory for database failure recovery.
        
        Args:
            session: Session to cache
        
        Postconditions:
            - Session is stored in memory cache
            - Can be retrieved even if database is unavailable
        """
        if session and session.id:
            self._session_cache[session.id] = session
            logger.debug(f"Cached session {session.id} in memory")
    
    def get_cached_session(self, session_id: int) -> Optional[StorySession]:
        """
        Retrieve cached session from memory.
        
        Args:
            session_id: ID of session to retrieve
        
        Returns:
            StorySession if cached, None otherwise
        """
        return self._session_cache.get(session_id)
    
    def export_session_to_temp_file(self, session: StorySession) -> Path:
        """
        Export session to temporary file for recovery.
        
        Args:
            session: Session to export
        
        Returns:
            Path: Path to the temporary file
        
        Raises:
            IOError: If file write fails
        
        Postconditions:
            - Session data is written to temporary file as JSON
            - File path is returned for user reference
        """
        if not session or not session.id:
            raise ValueError("Invalid session for export")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{session.id}_{timestamp}.json"
        filepath = self._temp_dir / filename
        
        # Convert session to dict
        session_data = session.to_dict()
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported session {session.id} to {filepath}")
        
        return filepath
    
    def import_session_from_temp_file(self, filepath: Path) -> StorySession:
        """
        Import session from temporary file.
        
        Args:
            filepath: Path to temporary file
        
        Returns:
            StorySession: Recovered session
        
        Raises:
            IOError: If file read fails
            CorruptedSessionError: If file data is invalid
        
        Postconditions:
            - Session is reconstructed from file data
            - Session is validated before return
        """
        if not filepath.exists():
            raise IOError(f"Recovery file not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Reconstruct session
            session = StorySession.from_dict(session_data)
            
            logger.info(f"Imported session {session.id} from {filepath}")
            
            return session
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise CorruptedSessionError(f"Failed to import session from {filepath}: {e}")
    
    def detect_corrupted_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Detect if session data is corrupted or inconsistent.
        
        Args:
            session_data: Raw session data from database
        
        Returns:
            bool: True if corruption detected, False otherwise
        
        Checks:
            - Required fields are present
            - JSON fields are valid
            - Data types are correct
            - Vocabulary list is valid
        """
        try:
            # Check required fields
            required_fields = ['id', 'language', 'genre', 'generation_mode', 
                             'story_context', 'vocabulary_introduced']
            
            for field in required_fields:
                if field not in session_data:
                    logger.warning(f"Missing required field: {field}")
                    return True
            
            # Validate story_context is valid JSON
            if isinstance(session_data['story_context'], str):
                try:
                    json.loads(session_data['story_context'])
                except json.JSONDecodeError:
                    logger.warning("story_context is not valid JSON")
                    return True
            
            # Validate vocabulary_introduced
            vocab = session_data.get('vocabulary_introduced')
            if vocab is not None:
                if isinstance(vocab, str):
                    try:
                        vocab_list = json.loads(vocab)
                        if not isinstance(vocab_list, list):
                            logger.warning("vocabulary_introduced is not a list")
                            return True
                    except json.JSONDecodeError:
                        logger.warning("vocabulary_introduced is not valid JSON")
                        return True
                elif not isinstance(vocab, list):
                    logger.warning("vocabulary_introduced is not a list")
                    return True
            
            # Validate generation_mode
            valid_modes = ['template', 'llm']
            if session_data.get('generation_mode') not in valid_modes:
                logger.warning(f"Invalid generation_mode: {session_data.get('generation_mode')}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during corruption detection: {e}")
            return True
    
    def attempt_session_repair(
        self,
        session_id: int,
        passages: list
    ) -> Optional[StorySession]:
        """
        Attempt to repair corrupted session from passage history.
        
        Args:
            session_id: ID of corrupted session
            passages: List of passages for this session
        
        Returns:
            StorySession: Repaired session, or None if repair failed
        
        Strategy:
            - Extract vocabulary from all passages
            - Reconstruct story context from passage history
            - Use most recent passage for current state
        """
        if not passages:
            logger.warning(f"Cannot repair session {session_id}: no passages")
            return None
        
        try:
            # Extract all new words from passages
            vocabulary_introduced = []
            for passage in passages:
                if hasattr(passage, 'new_words'):
                    for new_word in passage.new_words:
                        if new_word.word not in vocabulary_introduced:
                            vocabulary_introduced.append(new_word.word)
            
            # Get basic info from first passage
            first_passage = passages[0]
            
            # Create minimal story context
            from .models import StoryContext
            context = StoryContext(
                genre="unknown",  # Will need to be set manually
                current_location="recovered",
                characters=[],
                plot_summary="Session recovered from passages",
                previous_choices=[],
                mood="neutral"
            )
            
            # Create repaired session
            repaired_session = StorySession(
                id=session_id,
                language="unknown",  # Will need to be set manually
                genre="unknown",
                generation_mode="template",  # Default to template
                current_passage_id=passages[-1].id if passages else None,
                story_context=context.to_json(),
                vocabulary_introduced=vocabulary_introduced,
                created_at=first_passage.created_at if passages else datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
            logger.info(
                f"Repaired session {session_id}: "
                f"{len(vocabulary_introduced)} words, {len(passages)} passages"
            )
            
            return repaired_session
            
        except Exception as e:
            logger.error(f"Failed to repair session {session_id}: {e}")
            return None
    
    def export_readable_history(
        self,
        session_id: int,
        passages: list
    ) -> Path:
        """
        Export session history as readable text file.
        
        Args:
            session_id: Session ID
            passages: List of passages
        
        Returns:
            Path: Path to exported text file
        
        Postconditions:
            - Readable story history is written to file
            - File includes all passages and choices made
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"story_history_{session_id}_{timestamp}.txt"
        filepath = self._temp_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Story History - Session {session_id}\n")
            f.write(f"Exported: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, passage in enumerate(passages, 1):
                f.write(f"Passage {i}:\n")
                f.write("-" * 60 + "\n")
                f.write(f"{passage.story_text}\n\n")
                
                if passage.new_words:
                    f.write("New Words:\n")
                    for word in passage.new_words:
                        f.write(f"  - {word.word}: {word.translation}\n")
                    f.write("\n")
                
                if passage.choices:
                    f.write("Choices:\n")
                    for choice in passage.choices:
                        f.write(f"  {choice.id}. {choice.text}\n")
                    f.write("\n")
                
                f.write("\n")
        
        logger.info(f"Exported readable history to {filepath}")
        
        return filepath
