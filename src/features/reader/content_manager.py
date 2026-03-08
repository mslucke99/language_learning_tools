"""
Content manager for Immersive Reading Mode.

Manages content import, preprocessing, and storage for reading sessions.
Integrates with ContentParser and DifficultyCalculator for content analysis.
"""

import os
from typing import Dict, Optional
from src.core.database import FlashcardDatabase
from src.features.reader.content_parser import ContentParser
from src.features.reader.difficulty_calculator import DifficultyCalculator
from src.features.reader.exceptions import (
    AttestationRequiredError,
    InvalidContentError,
    FileTooLargeError
)


class ContentManager:
    """
    Manages content import, preprocessing, and storage.
    
    Responsibilities:
    - Import content from paste or file
    - Preprocess and segment content
    - Calculate difficulty scores
    - Store reading sessions with metadata
    - Manage reading progress
    """
    
    # Reading time estimation (words per minute)
    AVERAGE_READING_SPEED_WPM = 200
    
    # File size limit (5MB)
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
    
    # Minimum content length (characters)
    MIN_CONTENT_LENGTH = 100
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize the ContentManager.
        
        Args:
            db: FlashcardDatabase instance for data persistence
        """
        self.db = db
        self.parser = ContentParser()
        self.difficulty_calculator = DifficultyCalculator()
    
    def preprocess_content(self, raw_content: str) -> Dict:
        """
        Preprocess content for reading.
        
        Performs:
        - Text normalization
        - Sentence segmentation
        - Paragraph segmentation
        - Word count calculation
        - Reading time estimation
        
        Args:
            raw_content: Raw text content
            
        Returns:
            Dictionary containing:
            - content: Normalized full text (str)
            - sentences: List of sentence strings
            - paragraphs: List of paragraph strings
            - word_count: Number of words (int)
            - estimated_minutes: Estimated reading time in minutes (int)
        """
        # Parse the content using ContentParser
        parsed = self.parser.parse_content(raw_content)
        
        # Calculate estimated reading time
        word_count = parsed['word_count']
        estimated_minutes = max(1, round(word_count / self.AVERAGE_READING_SPEED_WPM))
        
        return {
            'content': parsed['content'],
            'sentences': parsed['sentences'],
            'paragraphs': parsed['paragraphs'],
            'word_count': word_count,
            'estimated_minutes': estimated_minutes
        }
    
    def calculate_difficulty(self, content: str, language: str) -> float:
        """
        Calculate difficulty score (0.0-1.0) based on vocabulary complexity.
        
        Uses DifficultyCalculator to analyze:
        - Vocabulary complexity (word length, diversity)
        - Sentence length
        - Grammatical complexity
        
        Args:
            content: Text content to analyze
            language: Target language code (e.g., 'en', 'ko', 'es')
            
        Returns:
            Difficulty score from 0.0 (easiest) to 1.0 (hardest)
        """
        result = self.difficulty_calculator.calculate_difficulty(content, language)
        return result['difficulty_score']

    def import_from_paste(
        self,
        content: str,
        title: str,
        language: str,
        user_attestation: bool,
        user_id: int = 1,
        import_ip_address: Optional[str] = None,
        import_user_agent: Optional[str] = None
    ) -> int:
        """
        Import content from user paste.
        
        Creates a reading session from pasted text content with full
        legal compliance tracking including attestation, audit trail,
        and privacy enforcement.
        
        Args:
            content: The pasted text content
            title: User-provided title for the content
            language: Target language code (e.g., 'en', 'ko', 'es')
            user_attestation: User confirms legal rights to content
            user_id: User ID (default: 1)
            import_ip_address: IP address for audit trail (optional)
            import_user_agent: User agent for audit trail (optional)
            
        Returns:
            reading_session_id: ID of created reading session
            
        Raises:
            AttestationRequiredError: If user_attestation is False
            InvalidContentError: If content is empty or too short
        """
        # Validate attestation requirement
        if not user_attestation:
            raise AttestationRequiredError(
                "You must confirm you have legal rights to this content. "
                "Please check the attestation box to proceed."
            )
        
        # Validate content
        if not content or not content.strip():
            raise InvalidContentError("Content cannot be empty")
        
        if len(content.strip()) < self.MIN_CONTENT_LENGTH:
            raise InvalidContentError(
                f"Content is too short (minimum {self.MIN_CONTENT_LENGTH} characters). "
                f"Current length: {len(content.strip())} characters."
            )
        
        # Preprocess content
        preprocessed = self.preprocess_content(content)
        
        # Calculate difficulty
        difficulty_score = self.calculate_difficulty(content, language)
        difficulty_rating = self._get_difficulty_rating(difficulty_score)
        
        # Create reading session in database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             content_type, difficulty_score, difficulty_rating, 
             word_count, estimated_minutes,
             legal_attestation, import_ip_address, import_user_agent,
             private, shareable, created_at)
            VALUES (?, ?, ?, ?, 'user_paste', 'paste', NULL, ?, ?, ?, ?, 1, ?, ?, 1, 0, CURRENT_TIMESTAMP)
        """, (
            user_id,
            title,
            preprocessed['content'],
            language,
            difficulty_score,
            difficulty_rating,
            preprocessed['word_count'],
            preprocessed['estimated_minutes'],
            import_ip_address,
            import_user_agent
        ))
        
        session_id = cursor.lastrowid
        
        # Create initial reading progress entry
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, ?, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id, user_id))
        
        self.db.conn.commit()
        
        return session_id
    
    def import_from_file(
        self,
        file_path: str,
        title: str,
        language: str,
        user_attestation: bool,
        user_id: int = 1,
        import_ip_address: Optional[str] = None,
        import_user_agent: Optional[str] = None
    ) -> int:
        """
        Import content from text file (.txt or .md).
        
        Reads a text file and creates a reading session with full
        legal compliance tracking. Supports multiple encodings
        (UTF-8, UTF-16, Latin-1) and validates file size limits.
        
        Args:
            file_path: Path to the file
            title: User-provided title for the content
            language: Target language code (e.g., 'en', 'ko', 'es')
            user_attestation: User confirms legal rights to content
            user_id: User ID (default: 1)
            import_ip_address: IP address for audit trail (optional)
            import_user_agent: User agent for audit trail (optional)
            
        Returns:
            reading_session_id: ID of created reading session
            
        Raises:
            AttestationRequiredError: If user_attestation is False
            InvalidContentError: If file not found, permission denied, or invalid format
            FileTooLargeError: If file exceeds 5MB limit
        """
        # Validate attestation requirement
        if not user_attestation:
            raise AttestationRequiredError(
                "You must confirm you have legal rights to this content. "
                "Please check the attestation box to proceed."
            )
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise InvalidContentError(f"File not found: {file_path}")
        
        # Check file size (max 5MB)
        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                raise FileTooLargeError(
                    f"File size ({size_mb:.1f}MB) exceeds the 5MB limit. "
                    f"Please split the content into smaller files."
                )
        except OSError as e:
            raise InvalidContentError(f"Cannot access file: {e}")
        
        # Read file with encoding detection
        content = None
        encodings = ['utf-8', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break  # Successfully read file
            except UnicodeDecodeError:
                continue  # Try next encoding
            except PermissionError:
                raise InvalidContentError(f"Permission denied: {file_path}")
            except Exception as e:
                raise InvalidContentError(f"Failed to read file: {e}")
        
        if content is None:
            raise InvalidContentError(
                f"Could not decode file with supported encodings: {', '.join(encodings)}"
            )
        
        # Validate content
        if not content.strip():
            raise InvalidContentError("File is empty")
        
        if len(content.strip()) < self.MIN_CONTENT_LENGTH:
            raise InvalidContentError(
                f"Content is too short (minimum {self.MIN_CONTENT_LENGTH} characters). "
                f"Current length: {len(content.strip())} characters."
            )
        
        # Preprocess content
        preprocessed = self.preprocess_content(content)
        
        # Calculate difficulty
        difficulty_score = self.calculate_difficulty(content, language)
        difficulty_rating = self._get_difficulty_rating(difficulty_score)
        
        # Create reading session in database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             content_type, difficulty_score, difficulty_rating, 
             word_count, estimated_minutes,
             legal_attestation, import_ip_address, import_user_agent,
             private, shareable, created_at)
            VALUES (?, ?, ?, ?, 'user_file', 'file', NULL, ?, ?, ?, ?, 1, ?, ?, 1, 0, CURRENT_TIMESTAMP)
        """, (
            user_id,
            title,
            preprocessed['content'],
            language,
            difficulty_score,
            difficulty_rating,
            preprocessed['word_count'],
            preprocessed['estimated_minutes'],
            import_ip_address,
            import_user_agent
        ))
        
        session_id = cursor.lastrowid
        
        # Create initial reading progress entry
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, ?, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id, user_id))
        
        self.db.conn.commit()
        
        return session_id
    
    def _get_difficulty_rating(self, difficulty_score: float) -> str:
        """
        Convert difficulty score to rating category.
        
        Args:
            difficulty_score: Score from 0.0 to 1.0
            
        Returns:
            Rating: 'easy', 'medium', or 'hard'
        """
        if difficulty_score < 0.33:
            return 'easy'
        elif difficulty_score < 0.67:
            return 'medium'
        else:
            return 'hard'
    
    def get_reading_session(self, session_id: int, user_id: int) -> Optional[Dict]:
        """
        Get reading session with ownership verification.
        
        Retrieves a reading session only if the requesting user owns it.
        Returns None if the session doesn't exist or the user is not authorized.
        This enforces privacy and access control (Requirements 2.3, 2.5).
        
        Args:
            session_id: Reading session ID
            user_id: Requesting user ID
            
        Returns:
            Dictionary containing session data and progress, or None if unauthorized/not found:
            {
                'id': int,
                'user_id': int,
                'title': str,
                'content': str,
                'language': str,
                'source': str,
                'import_method': str,
                'content_type': Optional[str],
                'difficulty_score': float,
                'difficulty_rating': str,
                'word_count': int,
                'estimated_minutes': int,
                'created_at': str,
                'last_read_at': Optional[str],
                'current_position': int,
                'current_paragraph': int,
                'completion_percentage': float,
                'time_spent_seconds': int,
                'completed': bool
            }
        """
        cursor = self.db.conn.cursor()
        
        # Query session with ownership verification
        cursor.execute("""
            SELECT 
                rs.id, rs.user_id, rs.title, rs.content, rs.language,
                rs.source, rs.import_method, rs.content_type,
                rs.difficulty_score, rs.difficulty_rating,
                rs.word_count, rs.estimated_minutes,
                rs.created_at, rs.last_read_at,
                rp.current_position, rp.current_paragraph,
                rp.completion_percentage, rp.time_spent_seconds,
                rp.completed
            FROM reading_sessions rs
            LEFT JOIN reading_progress rp ON rs.id = rp.session_id
            WHERE rs.id = ? AND rs.user_id = ?
        """, (session_id, user_id))
        
        row = cursor.fetchone()
        
        # Return None if not found or unauthorized
        if not row:
            return None
        
        # Build result dictionary
        return {
            'id': row[0],
            'user_id': row[1],
            'title': row[2],
            'content': row[3],
            'language': row[4],
            'source': row[5],
            'import_method': row[6],
            'content_type': row[7],
            'difficulty_score': row[8],
            'difficulty_rating': row[9],
            'word_count': row[10],
            'estimated_minutes': row[11],
            'created_at': row[12],
            'last_read_at': row[13],
            'current_position': row[14] if row[14] is not None else 0,
            'current_paragraph': row[15] if row[15] is not None else 0,
            'completion_percentage': row[16] if row[16] is not None else 0.0,
            'time_spent_seconds': row[17] if row[17] is not None else 0,
            'completed': bool(row[18]) if row[18] is not None else False
        }
    
    def update_reading_progress(
        self,
        session_id: int,
        current_position: int,
        completion_percentage: float,
        time_spent_seconds: int
    ) -> bool:
        """
        Update reading progress for a session.
        
        Updates the current reading position, completion percentage, and time spent.
        Also updates the last_read_at timestamp on the reading session.
        (Requirements 2.6, 10.2, 10.3, 10.4)
        
        Args:
            session_id: Reading session ID
            current_position: Current character offset in content
            completion_percentage: Completion percentage (0.0 to 100.0)
            time_spent_seconds: Total time spent reading in seconds
            
        Returns:
            True if update succeeded, False if session not found
        """
        cursor = self.db.conn.cursor()
        
        # Update reading progress
        cursor.execute("""
            UPDATE reading_progress
            SET current_position = ?,
                completion_percentage = ?,
                time_spent_seconds = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (current_position, completion_percentage, time_spent_seconds, session_id))
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            return False
        
        # Update last_read_at timestamp on the session
        cursor.execute("""
            UPDATE reading_sessions
            SET last_read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (session_id,))
        
        self.db.conn.commit()
        
        return True


    def get_reading_session(self, session_id: int, user_id: int) -> Optional[Dict]:
        """
        Get reading session with ownership verification.

        Retrieves a reading session only if the requesting user owns it.
        Returns None if the session doesn't exist or the user is not authorized.
        This enforces privacy and access control (Requirements 2.3, 2.5).

        Args:
            session_id: Reading session ID
            user_id: Requesting user ID

        Returns:
            Dictionary containing session data and progress, or None if unauthorized/not found:
            {
                'id': int,
                'user_id': int,
                'title': str,
                'content': str,
                'language': str,
                'source': str,
                'import_method': str,
                'content_type': Optional[str],
                'difficulty_score': float,
                'difficulty_rating': str,
                'word_count': int,
                'estimated_minutes': int,
                'created_at': str,
                'last_read_at': Optional[str],
                'current_position': int,
                'current_paragraph': int,
                'completion_percentage': float,
                'time_spent_seconds': int,
                'completed': bool
            }
        """
        cursor = self.db.conn.cursor()

        # Query session with ownership verification
        cursor.execute("""
            SELECT
                rs.id, rs.user_id, rs.title, rs.content, rs.language,
                rs.source, rs.import_method, rs.content_type,
                rs.difficulty_score, rs.difficulty_rating,
                rs.word_count, rs.estimated_minutes,
                rs.created_at, rs.last_read_at,
                rp.current_position, rp.current_paragraph,
                rp.completion_percentage, rp.time_spent_seconds,
                rp.completed
            FROM reading_sessions rs
            LEFT JOIN reading_progress rp ON rs.id = rp.session_id
            WHERE rs.id = ? AND rs.user_id = ?
        """, (session_id, user_id))

        row = cursor.fetchone()

        # Return None if not found or unauthorized
        if not row:
            return None

        # Build result dictionary
        return {
            'id': row[0],
            'user_id': row[1],
            'title': row[2],
            'content': row[3],
            'language': row[4],
            'source': row[5],
            'import_method': row[6],
            'content_type': row[7],
            'difficulty_score': row[8],
            'difficulty_rating': row[9],
            'word_count': row[10],
            'estimated_minutes': row[11],
            'created_at': row[12],
            'last_read_at': row[13],
            'current_position': row[14] if row[14] is not None else 0,
            'current_paragraph': row[15] if row[15] is not None else 0,
            'completion_percentage': row[16] if row[16] is not None else 0.0,
            'time_spent_seconds': row[17] if row[17] is not None else 0,
            'completed': bool(row[18]) if row[18] is not None else False
        }

    def update_reading_progress(
        self,
        session_id: int,
        current_position: int,
        completion_percentage: float,
        time_spent_seconds: int
    ) -> bool:
        """
        Update reading progress for a session.

        Updates the current reading position, completion percentage, and time spent.
        Also updates the last_read_at timestamp on the reading session.
        (Requirements 2.6, 10.2, 10.3, 10.4)

        Args:
            session_id: Reading session ID
            current_position: Current character offset in content
            completion_percentage: Completion percentage (0.0 to 100.0)
            time_spent_seconds: Total time spent reading in seconds

        Returns:
            True if update succeeded, False if session not found
        """
        cursor = self.db.conn.cursor()

        # Update reading progress
        cursor.execute("""
            UPDATE reading_progress
            SET current_position = ?,
                completion_percentage = ?,
                time_spent_seconds = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (current_position, completion_percentage, time_spent_seconds, session_id))

        # Check if any rows were updated
        if cursor.rowcount == 0:
            return False

        # Update last_read_at timestamp on the session
        cursor.execute("""
            UPDATE reading_sessions
            SET last_read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (session_id,))

        self.db.conn.commit()

        return True

