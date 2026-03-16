"""
Study Queue component for Context-Aware Sentence Mining.

Manages spaced repetition scheduling for sentences using the SM-2 algorithm.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result of a review action."""
    sentence_id: int
    next_review_date: str
    interval_days: int
    ease_factor: float
    total_reviews: int


@dataclass
class DueSentence:
    """Sentence due for review."""
    sentence_id: int
    content: str
    difficulty_score: float
    days_overdue: int
    last_reviewed: str


@dataclass
class ReviewStats:
    """Review statistics."""
    total_studied: int
    due_today: int
    overdue: int
    average_accuracy: float
    current_streak: int
    average_ease_factor: float
    by_difficulty: Dict[str, int]


class StudyQueue:
    """Manages spaced repetition scheduling using SM-2 algorithm."""
    
    # SM-2 algorithm constants
    DEFAULT_EASE_FACTOR = 2.5
    MIN_EASE_FACTOR = 1.3
    INITIAL_INTERVAL = 1  # days
    
    def __init__(self, db):
        """
        Initialize study queue with database access.
        
        Args:
            db: FlashcardDatabase instance
        """
        self.db = db
    
    def create_review_record(self, sentence_id: int) -> int:
        """
        Create initial review record when sentence first studied.
        
        Args:
            sentence_id: ID of sentence in imported_content table
            
        Returns:
            Review record ID
        """
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        next_review = (datetime.now() + timedelta(days=self.INITIAL_INTERVAL)).isoformat()
        
        cursor.execute("""
            INSERT INTO sentence_study_progress 
            (imported_content_id, last_reviewed, next_review_date, ease_factor, interval_days, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sentence_id, now, next_review, self.DEFAULT_EASE_FACTOR, self.INITIAL_INTERVAL, now))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def calculate_next_interval(self, current_interval: int, ease_factor: float, 
                                correct: bool) -> Tuple[int, float]:
        """
        Calculate next review interval using SM-2 algorithm.
        
        SM-2 Formula:
        - If correct: new_interval = current_interval * ease_factor
        - If incorrect: new_interval = 1 day
        - Ease factor adjusted: +0.1 if correct, -0.2 if incorrect (min 1.3)
        
        Args:
            current_interval: Current interval in days
            ease_factor: Current ease factor (default 2.5)
            correct: Whether review was correct
            
        Returns:
            Tuple of (new_interval_days, new_ease_factor)
        """
        if correct:
            # Increase interval by ease factor
            new_interval = max(1, int(current_interval * ease_factor))
            # Increase ease factor
            new_ease_factor = ease_factor + 0.1
        else:
            # Reset interval to 1 day
            new_interval = 1
            # Decrease ease factor (minimum 1.3)
            new_ease_factor = max(self.MIN_EASE_FACTOR, ease_factor - 0.2)
        
        return new_interval, new_ease_factor
    
    def record_review(self, sentence_id: int, correct: bool) -> ReviewResult:
        """
        Record a review and update scheduling parameters.
        
        Uses SM-2 algorithm to calculate next interval.
        
        Args:
            sentence_id: ID of reviewed sentence
            correct: Whether review was correct
            
        Returns:
            ReviewResult with updated scheduling info
        """
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        # Get current progress record
        cursor.execute("""
            SELECT id, interval_days, ease_factor, review_count, correct_count
            FROM sentence_study_progress
            WHERE imported_content_id = ?
        """, (sentence_id,))
        
        row = cursor.fetchone()
        
        if not row:
            # Create new record if doesn't exist
            self.create_review_record(sentence_id)
            cursor.execute("""
                SELECT id, interval_days, ease_factor, review_count, correct_count
                FROM sentence_study_progress
                WHERE imported_content_id = ?
            """, (sentence_id,))
            row = cursor.fetchone()
        
        progress_id, current_interval, ease_factor, review_count, correct_count = row
        
        # Calculate next interval and ease factor
        new_interval, new_ease_factor = self.calculate_next_interval(
            current_interval, ease_factor, correct
        )
        
        # Calculate next review date
        next_review_date = (datetime.now() + timedelta(days=new_interval)).isoformat()
        
        # Update progress record
        new_correct_count = correct_count + (1 if correct else 0)
        new_review_count = review_count + 1
        
        cursor.execute("""
            UPDATE sentence_study_progress
            SET last_reviewed = ?, next_review_date = ?, interval_days = ?, 
                ease_factor = ?, review_count = ?, correct_count = ?
            WHERE id = ?
        """, (now, next_review_date, new_interval, new_ease_factor, 
              new_review_count, new_correct_count, progress_id))
        
        self.db.conn.commit()
        
        return ReviewResult(
            sentence_id=sentence_id,
            next_review_date=next_review_date,
            interval_days=new_interval,
            ease_factor=new_ease_factor,
            total_reviews=new_review_count
        )
    
    def get_due_sentences(self, language: str, limit: int = 20) -> List[DueSentence]:
        """
        Get sentences due for review today.
        
        Args:
            language: Target language code
            limit: Maximum sentences to return
            
        Returns:
            List of due sentences, sorted by priority (overdue first)
        """
        cursor = self.db.conn.cursor()
        today = datetime.now().date().isoformat()
        
        cursor.execute("""
            SELECT ssp.imported_content_id, ic.content, ic.difficulty_score, 
                   ssp.last_reviewed, ssp.next_review_date
            FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND ssp.next_review_date <= ?
            ORDER BY ssp.next_review_date ASC
            LIMIT ?
        """, (language, today, limit))
        
        due_sentences = []
        
        for sentence_id, content, difficulty, last_reviewed, next_review_date in cursor.fetchall():
            # Calculate days overdue
            next_review = datetime.fromisoformat(next_review_date).date()
            today_date = datetime.now().date()
            days_overdue = (today_date - next_review).days
            
            due_sentences.append(DueSentence(
                sentence_id=sentence_id,
                content=content,
                difficulty_score=difficulty,
                days_overdue=days_overdue,
                last_reviewed=last_reviewed
            ))
        
        return due_sentences
    
    def get_review_statistics(self, language: str) -> ReviewStats:
        """
        Calculate review statistics for dashboard.
        
        Args:
            language: Target language code
            
        Returns:
            ReviewStats with counts, accuracy, streak, etc.
        """
        cursor = self.db.conn.cursor()
        today = datetime.now().date().isoformat()
        
        # Total studied
        cursor.execute("""
            SELECT COUNT(*) FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ?
        """, (language,))
        total_studied = cursor.fetchone()[0]
        
        # Due today
        cursor.execute("""
            SELECT COUNT(*) FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND ssp.next_review_date <= ?
        """, (language, today))
        due_today = cursor.fetchone()[0]
        
        # Overdue
        cursor.execute("""
            SELECT COUNT(*) FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND ssp.next_review_date < ?
        """, (language, today))
        overdue = cursor.fetchone()[0]
        
        # Average accuracy
        cursor.execute("""
            SELECT AVG(CAST(correct_count AS FLOAT) / review_count) FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND review_count > 0
        """, (language,))
        row = cursor.fetchone()
        average_accuracy = (row[0] * 100) if row and row[0] else 0.0
        
        # Average ease factor
        cursor.execute("""
            SELECT AVG(ease_factor) FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ?
        """, (language,))
        row = cursor.fetchone()
        average_ease_factor = row[0] if row and row[0] else self.DEFAULT_EASE_FACTOR
        
        # Difficulty distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN ic.difficulty_score <= 0.33 THEN 'easy'
                    WHEN ic.difficulty_score <= 0.66 THEN 'medium'
                    ELSE 'hard'
                END as difficulty,
                COUNT(*) as count
            FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND ic.difficulty_score IS NOT NULL
            GROUP BY difficulty
        """, (language,))
        
        by_difficulty = {}
        for difficulty, count in cursor.fetchall():
            by_difficulty[difficulty] = count
        
        # Study streak
        current_streak = self._calculate_study_streak(language)
        
        return ReviewStats(
            total_studied=total_studied,
            due_today=due_today,
            overdue=overdue,
            average_accuracy=average_accuracy,
            current_streak=current_streak,
            average_ease_factor=average_ease_factor,
            by_difficulty=by_difficulty
        )
    
    def _calculate_study_streak(self, language: str) -> int:
        """
        Calculate current study streak in consecutive days.
        
        Args:
            language: Target language code
            
        Returns:
            Number of consecutive days with reviews
        """
        cursor = self.db.conn.cursor()
        
        # Get distinct review dates in descending order
        cursor.execute("""
            SELECT DISTINCT DATE(last_reviewed) as review_date
            FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND last_reviewed IS NOT NULL
            ORDER BY review_date DESC
            LIMIT 30
        """, (language,))
        
        review_dates = [datetime.fromisoformat(row[0]).date() for row in cursor.fetchall()]
        
        if not review_dates:
            return 0
        
        # Check for consecutive days from today backwards
        today = datetime.now().date()
        streak = 0
        current_date = today
        
        for review_date in review_dates:
            if review_date == current_date or review_date == current_date - timedelta(days=1):
                streak += 1
                current_date = review_date
            else:
                break
        
        return streak
    
    def get_study_streak(self, language: str) -> int:
        """
        Calculate current study streak in consecutive days.
        
        Args:
            language: Target language code
            
        Returns:
            Number of consecutive days with reviews
        """
        return self._calculate_study_streak(language)
