"""
Reading Recommendations for Immersive Reading Mode.

Provides content recommendations based on user reading level
and content type preferences.
"""

from typing import Dict, List, Optional
from src.core.database import FlashcardDatabase


class ReadingRecommendations:
    """
    Generates content recommendations based on user reading level.
    
    Responsibilities:
    - Calculate user reading level from comprehension and speed
    - Recommend content slightly above user's current level
    - Prioritize content types user reads most frequently
    """
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize the ReadingRecommendations.
        
        Args:
            db: FlashcardDatabase instance for data access
        """
        self.db = db
    
    def calculate_user_reading_level(self, user_id: int) -> float:
        """
        Calculate user's reading level from comprehension and speed.
        
        Combines average comprehension score and reading speed to
        produce a reading level in the range [0.0, 1.0].
        
        Args:
            user_id: User ID
            
        Returns:
            Reading level from 0.0 (beginner) to 1.0 (advanced)
        """
        cursor = self.db.conn.cursor()
        
        # Get average comprehension score
        cursor.execute("""
            SELECT AVG(comprehension_score) as avg_comprehension
            FROM (
                SELECT 
                    session_id,
                    (1.0 - (lookup_count * 0.01)) as comprehension_score
                FROM reading_progress
                WHERE user_id = ? AND completed = 1
            )
        """, (user_id,))
        
        row = cursor.fetchone()
        avg_comprehension = row[0] if row[0] else 0.5
        
        # Get average reading speed (WPM)
        cursor.execute("""
            SELECT AVG(wpm) as avg_wpm
            FROM (
                SELECT 
                    session_id,
                    (words_read / (time_spent_seconds / 60.0)) as wpm
                FROM reading_progress
                WHERE user_id = ? AND time_spent_seconds > 0
            )
        """, (user_id,))
        
        row = cursor.fetchone()
        avg_wpm = row[0] if row[0] else 100  # Default to 100 WPM
        
        # Normalize WPM to 0-1 scale (typical range 50-300 WPM)
        wpm_normalized = min(1.0, max(0.0, (avg_wpm - 50) / 250))
        
        # Combine comprehension and speed (70% comprehension, 30% speed)
        reading_level = (avg_comprehension * 0.7) + (wpm_normalized * 0.3)
        
        return round(min(1.0, max(0.0, reading_level)), 2)
    
    def recommend_content(self, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Recommend content based on user's reading level and preferences.
        
        Args:
            user_id: User ID
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended session dictionaries
        """
        cursor = self.db.conn.cursor()
        
        # Calculate user's reading level
        user_level = self.calculate_user_reading_level(user_id)
        
        # Calculate target difficulty (slightly above user level)
        target_difficulty = min(1.0, user_level + 0.15)
        
        # Get content type frequency for user
        content_type_freq = self._get_content_type_frequency(user_id)
        
        # Get recommended content
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
            WHERE rs.user_id != ?  -- Don't recommend user's own content
                AND rs.difficulty_score >= ?  -- At or above target
                AND rs.difficulty_score <= ?  -- Not too difficult
                AND rs.private = 1
            ORDER BY 
                CASE rs.content_type
                    WHEN ? THEN 0
                    WHEN ? THEN 1
                    WHEN ? THEN 2
                    ELSE 3
                END,
                rs.difficulty_score ASC
            LIMIT ?
        """, (
            user_id,
            max(0.0, target_difficulty - 0.1),
            min(1.0, target_difficulty + 0.2),
            self._get_most_frequent_type(content_type_freq),
            self._get_second_frequent_type(content_type_freq),
            self._get_third_frequent_type(content_type_freq),
            limit
        ))
        
        recommendations = []
        for row in cursor.fetchall():
            recommendations.append({
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
        
        return recommendations
    
    def _get_content_type_frequency(self, user_id: int) -> Dict[str, int]:
        """Get content type frequency for a user."""
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
    
    def _get_most_frequent_type(self, frequency: Dict[str, int]) -> str:
        """Get most frequent content type."""
        if not frequency:
            return 'article'
        return max(frequency, key=frequency.get)
    
    def _get_second_frequent_type(self, frequency: Dict[str, int]) -> str:
        """Get second most frequent content type."""
        if len(frequency) < 2:
            return 'story'
        sorted_types = sorted(frequency, key=frequency.get, reverse=True)
        return sorted_types[1] if len(sorted_types) > 1 else 'story'
    
    def _get_third_frequent_type(self, frequency: Dict[str, int]) -> str:
        """Get third most frequent content type."""
        if len(frequency) < 3:
            return 'chapter'
        sorted_types = sorted(frequency, key=frequency.get, reverse=True)
        return sorted_types[2] if len(sorted_types) > 2 else 'chapter'
