"""
Reading Library for Immersive Reading Mode.

Provides reading library management with filtering, sorting,
and content type classification.
"""

from typing import Dict, List, Optional
from src.core.database import FlashcardDatabase


class ReadingLibrary:
    """
    Manages the reading library with filtering and sorting.
    
    Responsibilities:
    - Retrieve all reading sessions
    - Filter by completion status, difficulty, content type
    - Sort by recent activity, difficulty, title
    - Classify content types
    - Track content type frequency
    """
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize the ReadingLibrary.
        
        Args:
            db: FlashcardDatabase instance for data access
        """
        self.db = db
    
    def get_all_sessions(self, user_id: int) -> List[Dict]:
        """
        Get all reading sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session dictionaries with metadata and progress
        """
        cursor = self.db.conn.cursor()
        
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
            WHERE rs.user_id = ?
            ORDER BY rs.last_read_at DESC
        """, (user_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
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
            })
        
        return sessions
    
    def filter_sessions(
        self,
        user_id: int,
        completion_status: Optional[str] = None,
        difficulty: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter reading sessions by criteria.
        
        Args:
            user_id: User ID
            completion_status: Filter by 'in_progress', 'completed', or 'not_started'
            difficulty: Filter by 'easy', 'medium', or 'hard'
            content_type: Filter by 'article', 'story', 'chapter', or 'dialogue'
            
        Returns:
            List of filtered session dictionaries
        """
        cursor = self.db.conn.cursor()
        
        # Build query with filters
        query = """
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
            WHERE rs.user_id = ?
        """
        params = [user_id]
        
        # Add completion status filter
        if completion_status == 'in_progress':
            query += " AND rp.completed = 0 AND rp.completion_percentage > 0"
        elif completion_status == 'completed':
            query += " AND rp.completed = 1"
        elif completion_status == 'not_started':
            query += " AND (rp.completion_percentage = 0 OR rp.completion_percentage IS NULL)"
        
        # Add difficulty filter
        if difficulty:
            query += " AND rs.difficulty_rating = ?"
            params.append(difficulty)
        
        # Add content type filter
        if content_type:
            query += " AND rs.content_type = ?"
            params.append(content_type)
        
        query += " ORDER BY rs.last_read_at DESC"
        
        cursor.execute(query, params)
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
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
            })
        
        return sessions
    
    def sort_sessions(self, sessions: List[Dict], sort_by: str) -> List[Dict]:
        """
        Sort reading sessions by specified criteria.
        
        Args:
            sessions: List of session dictionaries
            sort_by: Sort criteria - 'recent', 'difficulty', or 'title'
            
        Returns:
            Sorted list of session dictionaries
        """
        if sort_by == 'recent':
            return sorted(
                sessions,
                key=lambda s: s.get('last_read_at') or '',
                reverse=True
            )
        elif sort_by == 'difficulty':
            return sorted(
                sessions,
                key=lambda s: s.get('difficulty_score', 0) or 0
            )
        elif sort_by == 'title':
            return sorted(
                sessions,
                key=lambda s: (s.get('title') or '').lower()
            )
        else:
            return sessions  # Return unchanged if unknown sort criteria
    
    def classify_content_type(self, content: str) -> str:
        """
        Classify content type based on structure and metadata.
        
        Analyzes content to determine if it's an article, story,
        chapter, or dialogue based on structure patterns.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Content type: 'article', 'story', 'chapter', or 'dialogue'
        """
        # Check for dialogue patterns (speaker labels, quotes)
        if self._is_dialogue(content):
            return 'dialogue'
        
        # Check for chapter patterns (chapter headings, numbered sections)
        if self._is_chapter(content):
            return 'chapter'
        
        # Check for story patterns (narrative structure, character development)
        if self._is_story(content):
            return 'story'
        
        # Default to article
        return 'article'
    
    def _is_dialogue(self, content: str) -> bool:
        """Check if content appears to be dialogue."""
        # Look for dialogue indicators
        dialogue_patterns = [
            '"',  # Quotation marks
            '“',  # Smart quotes
            '”',  # Smart quotes
            '-',  # Dialogue dashes
            '—',  # Em dash
        ]
        
        dialogue_count = sum(content.count(p) for p in dialogue_patterns)
        return dialogue_count > len(content) * 0.01  # More than 1% dialogue indicators
    
    def _is_chapter(self, content: str) -> bool:
        """Check if content appears to be a chapter."""
        # Look for chapter headings
        chapter_patterns = [
            r'chapter\s+\d+',  # Chapter 1, Chapter 12, etc.
            r'chapter\s+[a-zA-Z]',  # Chapter A, Chapter B, etc.
            r'^\d+\.\s+',  # Numbered sections like "1. Introduction"
        ]
        
        import re
        for pattern in chapter_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _is_story(self, content: str) -> bool:
        """Check if content appears to be a story."""
        # Look for narrative indicators
        story_indicators = [
            'once upon a time',  # Classic story starter
            'long ago',  # Story time marker
            'in a land',  # Fantasy story
            'there was',  # Story setup
            'the story',  # Story reference
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in story_indicators)
    
    def get_content_type_frequency(self, user_id: int) -> Dict[str, int]:
        """
        Get frequency of content types read by user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping content types to counts
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT content_type, COUNT(*) as count
            FROM reading_sessions
            WHERE user_id = ?
            GROUP BY content_type
        """, (user_id,))
        
        frequency = {}
        for row in cursor.fetchall():
            content_type = row[0]
            count = row[1]
            if content_type:
                frequency[content_type] = count
        
        return frequency
