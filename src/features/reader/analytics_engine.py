"""
Analytics Engine for tracking reading metrics.

This module provides the AnalyticsEngine class which tracks reading time,
calculates reading speed (WPM), and manages reading analytics.

Requirements: 7.1, 7.2
"""

from typing import Optional


class AnalyticsEngine:
    """Tracks and analyzes reading metrics."""
    
    def __init__(self, db):
        """
        Initialize the AnalyticsEngine.
        
        Args:
            db: FlashcardDatabase instance
        """
        self.db = db
    
    def track_reading_time(self, session_id: int, elapsed_seconds: int) -> None:
        """
        Track time spent reading.
        
        Updates the time_spent_seconds field in the reading_progress table
        for the specified session.
        
        Args:
            session_id: Reading session ID
            elapsed_seconds: Total elapsed time in seconds
            
        Requirements: 7.1
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            UPDATE reading_progress
            SET time_spent_seconds = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (elapsed_seconds, session_id))
        
        self.db.conn.commit()
    
    def calculate_reading_speed(
        self,
        session_id: int,
        words_read: int,
        time_seconds: int
    ) -> float:
        """
        Calculate reading speed in words per minute.
        
        Args:
            session_id: Reading session ID (for future use)
            words_read: Number of words read
            time_seconds: Time spent reading in seconds
            
        Returns:
            wpm: Words per minute (0.0 if time_seconds is 0)
            
        Requirements: 7.2
        """
        if time_seconds <= 0:
            return 0.0
        
        # Calculate WPM as (words_read / time_seconds) * 60
        wpm = (words_read / time_seconds) * 60
        
        return wpm

    def record_lookup(
        self,
        session_id: int,
        word: str,
        sentence_context: str,
        lookup_type: str = 'word'
    ) -> int:
        """
        Record a word/sentence lookup.

        Stores the lookup in the reading_lookups table. If the same word
        has been looked up previously in the same session, increments the
        lookup_count instead of creating a new record.

        Args:
            session_id: Reading session ID
            word: The word that was looked up
            sentence_context: Sentence containing the word
            lookup_type: Type of lookup ('word' or 'sentence')

        Returns:
            lookup_id: ID of the lookup record (new or existing)

        Requirements: 4.7, 4.8, 7.3
        """
        cursor = self.db.conn.cursor()

        # Check if this word was already looked up in this session
        cursor.execute("""
            SELECT id, lookup_count FROM reading_lookups
            WHERE session_id = ? AND word = ? AND lookup_type = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (session_id, word, lookup_type))

        existing = cursor.fetchone()

        if existing:
            # Increment lookup_count for existing lookup
            lookup_id = existing[0]
            new_count = existing[1] + 1

            cursor.execute("""
                UPDATE reading_lookups
                SET lookup_count = ?,
                    timestamp = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_count, lookup_id))
        else:
            # Create new lookup record
            cursor.execute("""
                INSERT INTO reading_lookups
                (session_id, user_id, lookup_type, word, sentence_context)
                VALUES (?, 1, ?, ?, ?)
            """, (session_id, lookup_type, word, sentence_context))
            lookup_id = cursor.lastrowid

        self.db.conn.commit()
        return lookup_id

    def calculate_comprehension_score(self, session_id: int) -> float:
        """
        Calculate comprehension score based on lookups and questions.

        The score is calculated based on:
        - Lookup frequency (fewer lookups = better comprehension)
        - Comprehension question accuracy (if questions exist)

        Args:
            session_id: Reading session ID

        Returns:
            score: Comprehension score in range [0.0, 1.0]

        Requirements: 7.4, 11.5
        """
        cursor = self.db.conn.cursor()

        # Get total words in the session
        cursor.execute("""
            SELECT word_count FROM reading_sessions
            WHERE id = ?
        """, (session_id,))
        result = cursor.fetchone()
        total_words = result[0] if result else 0

        # Get lookup count for this session
        cursor.execute("""
            SELECT COALESCE(SUM(lookup_count), 0) as lookup_count
            FROM reading_lookups
            WHERE session_id = ?
        """, (session_id,))
        result = cursor.fetchone()
        lookup_count = result[0] if result else 0

        # Get comprehension question results
        cursor.execute("""
            SELECT COUNT(*) as total_questions,
                   SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count
            FROM reading_comprehension
            WHERE session_id = ?
        """, (session_id,))
        result = cursor.fetchone()
        total_questions = result[0] if result else 0
        correct_count = result[1] if result else 0

        # Calculate lookup score component (0.0 to 1.0)
        # Fewer lookups = higher score
        if total_words > 0:
            lookup_ratio = lookup_count / total_words
            # Score decreases as lookup ratio increases
            # If lookup_ratio is 0, lookup_score = 1.0
            # If lookup_ratio is 0.1 (10% words looked up), lookup_score = 0.5
            lookup_score = max(0.0, 1.0 - (lookup_ratio * 5))
        else:
            lookup_score = 1.0

        # Calculate question score component (0.0 to 1.0)
        if total_questions > 0:
            question_score = correct_count / total_questions
        else:
            # No questions answered, give partial credit based on lookups
            question_score = 0.5

        # Combine scores (60% question score, 40% lookup score)
        comprehension_score = (question_score * 0.6) + (lookup_score * 0.4)

        # Ensure score is in valid range
        return max(0.0, min(1.0, comprehension_score))

    def get_session_statistics(self, session_id: int) -> dict:
        """
        Get statistics for a reading session.

        Args:
            session_id: Reading session ID

        Returns:
            Dictionary with:
                - time_spent_seconds: int
                - words_read: int
                - wpm: float
                - lookup_count: int
                - comprehension_score: float
                - completion_percentage: float
        """
        cursor = self.db.conn.cursor()

        # Get progress data
        cursor.execute("""
            SELECT
                time_spent_seconds,
                current_position,
                completion_percentage
            FROM reading_progress
            WHERE session_id = ?
        """, (session_id,))
        progress = cursor.fetchone()

        if not progress:
            return {
                'time_spent_seconds': 0,
                'words_read': 0,
                'wpm': 0.0,
                'lookup_count': 0,
                'comprehension_score': 0.0,
                'completion_percentage': 0.0
            }

        time_spent_seconds = progress[0]
        current_position = progress[1]
        completion_percentage = progress[2] if progress[2] else 0.0

        # Get word count from session
        cursor.execute("""
            SELECT word_count FROM reading_sessions WHERE id = ?
        """, (session_id,))
        session_result = cursor.fetchone()
        words_read = int(current_position / 5) if session_result is None else session_result[0]

        # Calculate WPM
        wpm = self.calculate_reading_speed(session_id, words_read, time_spent_seconds)

        # Get lookup count
        cursor.execute("""
            SELECT COALESCE(SUM(lookup_count), 0) FROM reading_lookups
            WHERE session_id = ?
        """, (session_id,))
        lookup_result = cursor.fetchone()
        lookup_count = lookup_result[0] if lookup_result else 0

        # Get comprehension score
        comprehension_score = self.calculate_comprehension_score(session_id)

        return {
            'time_spent_seconds': time_spent_seconds,
            'words_read': words_read,
            'wpm': wpm,
            'lookup_count': lookup_count,
            'comprehension_score': comprehension_score,
            'completion_percentage': completion_percentage
        }

    def mark_session_completed(self, session_id: int) -> bool:
        """
        Mark a reading session as completed.

        Args:
            session_id: Reading session ID

        Returns:
            True if session was marked completed, False otherwise
        """
        cursor = self.db.conn.cursor()

        # Check if session exists
        cursor.execute("""
            SELECT id FROM reading_sessions WHERE id = ?
        """, (session_id,))
        if not cursor.fetchone():
            return False

        # Update progress to mark as completed
        cursor.execute("""
            UPDATE reading_progress
            SET completed = 1,
                completed_at = CURRENT_TIMESTAMP,
                last_updated = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))

        # Update last_read_at in reading_sessions
        cursor.execute("""
            UPDATE reading_sessions
            SET last_read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (session_id,))

        self.db.conn.commit()
        return True

    def get_aggregate_statistics(self, user_id: int) -> dict:
        """
        Get aggregate reading statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with:
                - total_time_seconds: int
                - total_sessions: int
                - average_wpm: float
                - total_words_learned: int
                - current_streak_days: int
                - longest_streak_days: int
        """
        cursor = self.db.conn.cursor()

        # Get total time and session count
        cursor.execute("""
            SELECT
                COALESCE(SUM(time_spent_seconds), 0) as total_time,
                COUNT(DISTINCT session_id) as total_sessions
            FROM reading_progress
            WHERE session_id IN (
                SELECT id FROM reading_sessions WHERE user_id = ?
            )
        """, (user_id,))
        result = cursor.fetchone()
        total_time_seconds = result[0] if result else 0
        total_sessions = result[1] if result else 0

        # Get total words learned (from lookups)
        cursor.execute("""
            SELECT COUNT(DISTINCT word) FROM reading_lookups
            WHERE session_id IN (
                SELECT id FROM reading_sessions WHERE user_id = ?
            )
        """, (user_id,))
        result = cursor.fetchone()
        total_words_learned = result[0] if result else 0

        # Calculate average WPM
        # Get all sessions with their time and word counts
        cursor.execute("""
            SELECT
                p.time_spent_seconds,
                s.word_count
            FROM reading_progress p
            JOIN reading_sessions s ON p.session_id = s.id
            WHERE s.user_id = ?
            AND p.time_spent_seconds > 0
            AND s.word_count > 0
        """, (user_id,))
        sessions_data = cursor.fetchall()

        if sessions_data:
            total_wpm = 0
            valid_sessions = 0
            for time_spent, word_count in sessions_data:
                if time_spent > 0:
                    wpm = (word_count / time_spent) * 60
                    total_wpm += wpm
                    valid_sessions += 1

            average_wpm = total_wpm / valid_sessions if valid_sessions > 0 else 0.0
        else:
            average_wpm = 0.0

        # Calculate reading streaks
        current_streak_days = self.calculate_current_streak(user_id)
        longest_streak_days = self.calculate_longest_streak(user_id)

        return {
            'total_time_seconds': total_time_seconds,
            'total_sessions': total_sessions,
            'average_wpm': average_wpm,
            'total_words_learned': total_words_learned,
            'current_streak_days': current_streak_days,
            'longest_streak_days': longest_streak_days
        }

    def calculate_current_streak(self, user_id: int) -> int:
        """
        Calculate the current reading streak (consecutive days with reading).

        A day counts toward the streak if the user reads for at least 5 minutes.

        Args:
            user_id: User ID

        Returns:
            Number of consecutive days with reading activity
        """
        cursor = self.db.conn.cursor()

        # Get distinct days with reading time >= 5 minutes (300 seconds)
        cursor.execute("""
            SELECT DISTINCT DATE(last_updated) as read_date
            FROM reading_progress
            WHERE session_id IN (
                SELECT id FROM reading_sessions WHERE user_id = ?
            )
            AND time_spent_seconds >= 300
            ORDER BY read_date DESC
        """, (user_id,))
        dates = [row[0] for row in cursor.fetchall()]

        if not dates:
            return 0

        # Calculate consecutive days from most recent
        from datetime import datetime, timedelta

        current_streak = 0
        expected_date = datetime.strptime(dates[0], '%Y-%m-%d')

        for date_str in dates:
            actual_date = datetime.strptime(date_str, '%Y-%m-%d')

            # Check if this is the expected consecutive day
            if actual_date == expected_date or actual_date == expected_date - timedelta(days=1):
                current_streak += 1
                expected_date = actual_date
            else:
                break

        return current_streak

    def calculate_longest_streak(self, user_id: int) -> int:
        """
        Calculate the longest reading streak ever achieved.

        Args:
            user_id: User ID

        Returns:
            Longest streak of consecutive days with reading activity
        """
        cursor = self.db.conn.cursor()

        # Get all distinct days with reading time >= 5 minutes
        cursor.execute("""
            SELECT DISTINCT DATE(last_updated) as read_date
            FROM reading_progress
            WHERE session_id IN (
                SELECT id FROM reading_sessions WHERE user_id = ?
            )
            AND time_spent_seconds >= 300
            ORDER BY read_date ASC
        """, (user_id,))
        dates = [row[0] for row in cursor.fetchall()]

        if not dates:
            return 0

        from datetime import datetime, timedelta

        longest_streak = 1
        current_streak = 1

        for i in range(1, len(dates)):
            prev_date = datetime.strptime(dates[i-1], '%Y-%m-%d')
            curr_date = datetime.strptime(dates[i], '%Y-%m-%d')

            if curr_date == prev_date + timedelta(days=1):
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1

        return longest_streak
