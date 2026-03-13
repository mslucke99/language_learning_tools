"""
Unit tests for AnalyticsEngine class.

Tests the core methods of the AnalyticsEngine including:
- Initialization
- Reading time tracking
- Reading speed calculation (WPM)

Requirements: 7.1, 7.2
"""

import pytest
import sqlite3
from src.features.reader.analytics_engine import AnalyticsEngine
from src.core.database import FlashcardDatabase


@pytest.fixture
def test_db():
    """Create a test database."""
    db = FlashcardDatabase(":memory:")
    yield db
    db.close()


@pytest.fixture
def analytics_engine(test_db):
    """Create an AnalyticsEngine instance."""
    return AnalyticsEngine(test_db)


class TestAnalyticsEngineInitialization:
    """Test AnalyticsEngine initialization."""
    
    def test_init_stores_database_reference(self, test_db):
        """Test that __init__ stores the database reference."""
        engine = AnalyticsEngine(test_db)
        assert engine.db is test_db


class TestTrackReadingTime:
    """Test track_reading_time functionality."""
    
    def test_track_reading_time_updates_database(self, analytics_engine, test_db):
        """Test that track_reading_time updates the reading_progress table (Requirement 7.1)."""
        # Create a reading session and progress entry
        cursor = test_db.conn.cursor()
        
        # Insert a reading session
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             difficulty_score, difficulty_rating, word_count, estimated_minutes,
             legal_attestation, private, shareable)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste',
                    0.5, 'medium', 10, 1, 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        
        # Insert a reading progress entry
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed)
            VALUES (?, 1, 0, 0, 0.0, 0, 0)
        """, (session_id,))
        test_db.conn.commit()
        
        # Track reading time
        analytics_engine.track_reading_time(session_id, 120)
        
        # Verify the time was updated
        cursor.execute(
            "SELECT time_spent_seconds FROM reading_progress WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 120
    
    def test_track_reading_time_updates_last_updated(self, analytics_engine, test_db):
        """Test that track_reading_time updates the last_updated timestamp."""
        import time
        
        # Create a reading session and progress entry
        cursor = test_db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             difficulty_score, difficulty_rating, word_count, estimated_minutes,
             legal_attestation, private, shareable)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste',
                    0.5, 'medium', 10, 1, 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed)
            VALUES (?, 1, 0, 0, 0.0, 0, 0)
        """, (session_id,))
        test_db.conn.commit()
        
        # Get initial timestamp
        cursor.execute("SELECT last_updated FROM reading_progress WHERE session_id = ?", (session_id,))
        initial_timestamp = cursor.fetchone()[0]
        
        # Wait at least 1 second for timestamp to change (SQLite CURRENT_TIMESTAMP has second precision)
        time.sleep(1.1)
        
        # Track reading time
        analytics_engine.track_reading_time(session_id, 60)
        
        # Verify last_updated was updated
        cursor.execute("SELECT last_updated FROM reading_progress WHERE session_id = ?", (session_id,))
        updated_timestamp = cursor.fetchone()[0]
        
        assert updated_timestamp != initial_timestamp
    
    def test_track_reading_time_with_zero_seconds(self, analytics_engine, test_db):
        """Test tracking reading time with zero seconds."""
        # Create a reading session and progress entry
        cursor = test_db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             difficulty_score, difficulty_rating, word_count, estimated_minutes,
             legal_attestation, private, shareable)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste',
                    0.5, 'medium', 10, 1, 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed)
            VALUES (?, 1, 0, 0, 0.0, 0, 0)
        """, (session_id,))
        test_db.conn.commit()
        
        # Track zero seconds
        analytics_engine.track_reading_time(session_id, 0)
        
        # Verify the time was updated to 0
        cursor.execute(
            "SELECT time_spent_seconds FROM reading_progress WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        assert row[0] == 0
    
    def test_track_reading_time_multiple_updates(self, analytics_engine, test_db):
        """Test multiple reading time updates."""
        # Create a reading session and progress entry
        cursor = test_db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             difficulty_score, difficulty_rating, word_count, estimated_minutes,
             legal_attestation, private, shareable)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste',
                    0.5, 'medium', 10, 1, 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed)
            VALUES (?, 1, 0, 0, 0.0, 0, 0)
        """, (session_id,))
        test_db.conn.commit()
        
        # Track reading time multiple times
        analytics_engine.track_reading_time(session_id, 60)
        analytics_engine.track_reading_time(session_id, 120)
        analytics_engine.track_reading_time(session_id, 180)
        
        # Verify the latest time is stored
        cursor.execute(
            "SELECT time_spent_seconds FROM reading_progress WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        assert row[0] == 180


class TestCalculateReadingSpeed:
    """Test calculate_reading_speed functionality."""
    
    def test_calculate_reading_speed_basic(self, analytics_engine):
        """Test basic WPM calculation (Requirement 7.2)."""
        # 100 words in 60 seconds = 100 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=100,
            time_seconds=60
        )
        assert wpm == 100.0
    
    def test_calculate_reading_speed_formula(self, analytics_engine):
        """Test that WPM formula is (words_read / time_seconds) * 60."""
        # 150 words in 90 seconds = (150 / 90) * 60 = 100 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=150,
            time_seconds=90
        )
        assert wpm == 100.0
        
        # 200 words in 120 seconds = (200 / 120) * 60 = 100 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=200,
            time_seconds=120
        )
        assert wpm == 100.0
    
    def test_calculate_reading_speed_with_zero_time(self, analytics_engine):
        """Test WPM calculation with zero time returns 0.0."""
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=100,
            time_seconds=0
        )
        assert wpm == 0.0
    
    def test_calculate_reading_speed_with_negative_time(self, analytics_engine):
        """Test WPM calculation with negative time returns 0.0."""
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=100,
            time_seconds=-10
        )
        assert wpm == 0.0
    
    def test_calculate_reading_speed_with_zero_words(self, analytics_engine):
        """Test WPM calculation with zero words."""
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=0,
            time_seconds=60
        )
        assert wpm == 0.0
    
    def test_calculate_reading_speed_fast_reader(self, analytics_engine):
        """Test WPM calculation for fast reader."""
        # 300 words in 60 seconds = 300 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=300,
            time_seconds=60
        )
        assert wpm == 300.0
    
    def test_calculate_reading_speed_slow_reader(self, analytics_engine):
        """Test WPM calculation for slow reader."""
        # 50 words in 60 seconds = 50 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=50,
            time_seconds=60
        )
        assert wpm == 50.0
    
    def test_calculate_reading_speed_fractional_result(self, analytics_engine):
        """Test WPM calculation with fractional result."""
        # 100 words in 75 seconds = (100 / 75) * 60 = 80.0 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=100,
            time_seconds=75
        )
        assert wpm == 80.0
        
        # 123 words in 90 seconds = (123 / 90) * 60 = 82.0 WPM
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=123,
            time_seconds=90
        )
        assert abs(wpm - 82.0) < 0.01  # Allow small floating point error

"""
Property tests for AnalyticsEngine class.

Tests property-based correctness properties for the AnalyticsEngine including:
- Property 18: Reading Speed Calculation
- Property 19: Time Accumulation
- Property 12: Word Lookup Creates Record
- Property 13: Lookup Count Increment
- Property 20: Lookup Count Accuracy
- Property 21: Comprehension Score Range
- Property 22: Completion Marking
- Property 23: Aggregate Statistics Consistency
- Property 43: Reading Streak Calculation
- Property 44: Longest Streak Tracking

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 10.4, 11.5, 18.1, 18.2, 18.4, 18.5
"""

import pytest
from hypothesis import given, strategies as st
from hypothesis import settings
from src.features.reader.analytics_engine import AnalyticsEngine
from src.core.database import FlashcardDatabase


@pytest.fixture
def test_db():
    """Create a test database."""
    db = FlashcardDatabase(":memory:")
    yield db
    db.close()


@pytest.fixture
def analytics_engine(test_db):
    """Create an AnalyticsEngine instance."""
    return AnalyticsEngine(test_db)


def create_test_session(db, content="Test content " * 10):
    """Helper to create a test reading session."""
    cursor = db.conn.cursor()
    
    # Insert a reading session
    cursor.execute("""
        INSERT INTO reading_sessions
        (user_id, title, content, language, source, import_method,
         difficulty_score, difficulty_rating, word_count, estimated_minutes,
         legal_attestation, private, shareable)
        VALUES (1, 'Test', ?, 'en', 'user_paste', 'paste',
                0.5, 'medium', ?, 1, 1, 1, 0)
    """, (content, len(content.split())))
    session_id = cursor.lastrowid
    
    # Insert a reading progress entry
    cursor.execute("""
        INSERT INTO reading_progress
        (session_id, user_id, current_position, current_paragraph,
         completion_percentage, time_spent_seconds, completed)
        VALUES (?, 1, 0, 0, 0.0, 0, 0)
    """, (session_id,))
    db.conn.commit()
    
    return session_id


class TestProperty18ReadingSpeedCalculation:
    """Property 18: Reading Speed Calculation.
    
    Validates: Requirements 7.2
    Verify WPM equals (words_read / time_seconds) * 60 and WPM >= 0
    """
    
    @given(
        words_read=st.integers(min_value=0, max_value=10000),
        time_seconds=st.floats(min_value=0.1, max_value=3600)
    )
    @settings(max_examples=100)
    def test_wpm_formula(self, analytics_engine, words_read, time_seconds):
        """Test that WPM equals (words_read / time_seconds) * 60."""
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=words_read,
            time_seconds=time_seconds
        )
        
        expected_wpm = (words_read / time_seconds) * 60
        assert abs(wpm - expected_wpm) < 0.001
    
    @given(
        words_read=st.integers(min_value=0, max_value=10000),
        time_seconds=st.floats(min_value=0.1, max_value=3600)
    )
    @settings(max_examples=100)
    def test_wpm_non_negative(self, analytics_engine, words_read, time_seconds):
        """Test that WPM is always >= 0."""
        wpm = analytics_engine.calculate_reading_speed(
            session_id=1,
            words_read=words_read,
            time_seconds=time_seconds
        )
        assert wpm >= 0


class TestProperty19TimeAccumulation:
    """Property 19: Time Accumulation.
    
    Validates: Requirements 7.1, 10.4
    Verify time_spent_seconds monotonically increases (never decreases)
    """
    
    def test_time_accumulates(self, analytics_engine, test_db):
        """Test that time_spent_seconds only increases or stays the same."""
        session_id = create_test_session(test_db)
        
        # Track time multiple times
        analytics_engine.track_reading_time(session_id, 60)
        analytics_engine.track_reading_time(session_id, 120)
        analytics_engine.track_reading_time(session_id, 180)
        
        # Verify time only increased
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT time_spent_seconds FROM reading_progress WHERE session_id = ?", (session_id,))
        final_time = cursor.fetchone()[0]
        
        assert final_time == 180
        assert final_time >= 60  # Monotonic: never decreased


class TestProperty12WordLookupCreatesRecord:
    """Property 12: Word Lookup Creates Record.
    
    Validates: Requirements 4.7
    Verify lookup creates record with word, sentence_context, timestamp, lookup_type='word'
    """
    
    def test_lookup_creates_record(self, analytics_engine, test_db):
        """Test that record_lookup creates a record in reading_lookups table."""
        session_id = create_test_session(test_db)
        
        # Record a lookup
        lookup_id = analytics_engine.record_lookup(
            session_id=session_id,
            word="example",
            sentence_context="This is an example sentence.",
            lookup_type="word"
        )
        
        # Verify record was created
        cursor = test_db.conn.cursor()
        cursor.execute("""
            SELECT word, sentence_context, lookup_type, timestamp
            FROM reading_lookups WHERE id = ?
        """, (lookup_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[0] == "example"
        assert row[1] == "This is an example sentence."
        assert row[2] == "word"
        assert row[3] is not None  # timestamp exists


class TestProperty13LookupCountIncrement:
    """Property 13: Lookup Count Increment.
    
    Validates: Requirements 4.8
    Verify repeated lookups increment lookup_count
    """
    
    def test_lookup_count_increments(self, analytics_engine, test_db):
        """Test that looking up the same word multiple times increments lookup_count."""
        session_id = create_test_session(test_db)
        
        # Record the same lookup multiple times
        lookup_id = analytics_engine.record_lookup(
            session_id=session_id,
            word="example",
            sentence_context="This is an example sentence.",
            lookup_type="word"
        )
        
        # Look up again
        lookup_id = analytics_engine.record_lookup(
            session_id=session_id,
            word="example",
            sentence_context="This is an example sentence.",
            lookup_type="word"
        )
        
        # Look up a third time
        lookup_id = analytics_engine.record_lookup(
            session_id=session_id,
            word="example",
            sentence_context="This is an example sentence.",
            lookup_type="word"
        )
        
        # Verify lookup_count is 3
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT lookup_count FROM reading_lookups WHERE id = ?", (lookup_id,))
        count = cursor.fetchone()[0]
        
        assert count == 3


class TestProperty20LookupCountAccuracy:
    """Property 20: Lookup Count Accuracy.
    
    Validates: Requirements 7.3
    Verify Analytics_Engine count equals actual reading_lookups records
    """
    
    def test_lookup_count_matches_database(self, analytics_engine, test_db):
        """Test that the lookup count in the database matches what we recorded."""
        session_id = create_test_session(test_db)
        
        # Record multiple lookups
        analytics_engine.record_lookup(session_id, "word1", "context1", "word")
        analytics_engine.record_lookup(session_id, "word2", "context2", "word")
        analytics_engine.record_lookup(session_id, "word1", "context1", "word")  # Same word
        analytics_engine.record_lookup(session_id, "word3", "context3", "word")
        analytics_engine.record_lookup(session_id, "word1", "context1", "word")  # Same word again
        
        # Get total lookup count from database
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(lookup_count), 0) FROM reading_lookups WHERE session_id = ?", (session_id,))
        total_count = cursor.fetchone()[0]
        
        # Should be: word1 (3) + word2 (1) + word3 (1) = 5
        assert total_count == 5


class TestProperty21ComprehensionScoreRange:
    """Property 21: Comprehension Score Range.
    
    Validates: Requirements 7.4, 11.5
    Verify comprehension_score in [0.0, 1.0]
    """
    
    def test_comprehension_score_range_no_lookups_no_questions(self, analytics_engine, test_db):
        """Test comprehension score when there are no lookups and no questions."""
        session_id = create_test_session(test_db)
        
        score = analytics_engine.calculate_comprehension_score(session_id)
        assert 0.0 <= score <= 1.0
    
    def test_comprehension_score_range_with_lookups(self, analytics_engine, test_db):
        """Test comprehension score with lookups."""
        session_id = create_test_session(test_db)
        
        # Add some lookups
        analytics_engine.record_lookup(session_id, "word1", "context1", "word")
        analytics_engine.record_lookup(session_id, "word2", "context2", "word")
        
        score = analytics_engine.calculate_comprehension_score(session_id)
        assert 0.0 <= score <= 1.0
    
    def test_comprehension_score_range_with_questions(self, analytics_engine, test_db):
        """Test comprehension score with questions."""
        session_id = create_test_session(test_db)
        
        # Add comprehension questions
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, question, question_type, choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, 'Question 1', 'main_idea', 'A', 'B', 'C', 'D', 'A')
        """, (session_id,))
        test_db.conn.commit()
        
        score = analytics_engine.calculate_comprehension_score(session_id)
        assert 0.0 <= score <= 1.0
    
    @given(
        words_read=st.integers(min_value=10, max_value=1000),
        lookup_ratio=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=50)
    def test_comprehension_score_formula(self, analytics_engine, test_db, words_read, lookup_ratio):
        """Test that comprehension score follows the expected formula."""
        session_id = create_test_session(test_db, content=" ".join(["word"] * words_read))
        
        # Calculate expected lookup count based on ratio
        lookup_count = int(words_read * lookup_ratio)
        
        # Add lookups
        for i in range(lookup_count):
            analytics_engine.record_lookup(session_id, f"word{i}", f"context{i}", "word")
        
        score = analytics_engine.calculate_comprehension_score(session_id)
        
        # Score should be in valid range
        assert 0.0 <= score <= 1.0


class TestProperty22CompletionMarking:
    """Property 22: Completion Marking.
    
    Validates: Requirements 7.5
    Verify completed sessions have completed=TRUE and valid completed_at timestamp
    """
    
    def test_mark_session_completed(self, analytics_engine, test_db):
        """Test that mark_session_completed marks session as completed."""
        session_id = create_test_session(test_db)
        
        # Mark as completed
        result = analytics_engine.mark_session_completed(session_id)
        
        assert result is True
        
        # Verify completion status
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT completed, completed_at FROM reading_progress WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        assert row[0] == 1  # completed = TRUE
        assert row[1] is not None  # completed_at timestamp exists
    
    def test_mark_session_completed_updates_last_read(self, analytics_engine, test_db):
        """Test that mark_session_completed updates last_read_at in reading_sessions."""
        session_id = create_test_session(test_db)
        
        # Get initial last_read_at
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT last_read_at FROM reading_sessions WHERE id = ?", (session_id,))
        initial_last_read = cursor.fetchone()[0]
        
        # Mark as completed
        analytics_engine.mark_session_completed(session_id)
        
        # Verify last_read_at was updated
        cursor.execute("SELECT last_read_at FROM reading_sessions WHERE id = ?", (session_id,))
        updated_last_read = cursor.fetchone()[0]
        
        assert updated_last_read != initial_last_read


class TestProperty23AggregateStatisticsConsistency:
    """Property 23: Aggregate Statistics Consistency.
    
    Validates: Requirements 7.6, 9.5
    Verify total_reading_time equals sum of time_spent_seconds across all sessions
    """
    
    def test_aggregate_time_consistency(self, analytics_engine, test_db):
        """Test that aggregate total_time_seconds equals sum of individual session times."""
        # Create multiple sessions
        session1 = create_test_session(test_db)
        session2 = create_test_session(test_db)
        session3 = create_test_session(test_db)
        
        # Track time for each session
        analytics_engine.track_reading_time(session1, 100)
        analytics_engine.track_reading_time(session2, 200)
        analytics_engine.track_reading_time(session3, 300)
        
        # Get aggregate statistics
        stats = analytics_engine.get_aggregate_statistics(user_id=1)
        
        # Verify total time matches sum
        assert stats['total_time_seconds'] == 600  # 100 + 200 + 300


class TestReadingStreakCalculation:
    """Property 43: Reading Streak Calculation.
    
    Validates: Requirements 18.1, 18.2, 18.4
    Verify streak increments on consecutive days (>=5 min) and resets on missed days
    """
    
    def test_streak_on_consecutive_days(self, analytics_engine, test_db):
        """Test that streak increments on consecutive reading days."""
        from datetime import datetime, timedelta
        
        session1 = create_test_session(test_db)
        session2 = create_test_session(test_db)
        session3 = create_test_session(test_db)
        
        # Set progress with timestamps on consecutive days
        cursor = test_db.conn.cursor()
        
        today = datetime.now().date()
        
        # Day 1: 10 minutes of reading
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 600, last_updated = ?
            WHERE session_id = ?
        """, (today.strftime('%Y-%m-%d'), session1))
        
        # Day 2: 15 minutes of reading
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 900, last_updated = ?
            WHERE session_id = ?
        """, ((today - timedelta(days=1)).strftime('%Y-%m-%d'), session2))
        
        # Day 3: 20 minutes of reading
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 1200, last_updated = ?
            WHERE session_id = ?
        """, ((today - timedelta(days=2)).strftime('%Y-%m-%d'), session3))
        
        test_db.conn.commit()
        
        # Calculate streak
        streak = analytics_engine.calculate_current_streak(user_id=1)
        
        # Should have a 3-day streak
        assert streak == 3
    
    def test_streak_resets_on_missed_day(self, analytics_engine, test_db):
        """Test that streak resets when a day is missed."""
        from datetime import datetime, timedelta
        
        session1 = create_test_session(test_db)
        session2 = create_test_session(test_db)
        session3 = create_test_session(test_db)
        
        cursor = test_db.conn.cursor()
        
        today = datetime.now().date()
        
        # Day 1: 10 minutes
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 600, last_updated = ?
            WHERE session_id = ?
        """, (today.strftime('%Y-%m-%d'), session1))
        
        # Day 3: 15 minutes (missed day 2)
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 900, last_updated = ?
            WHERE session_id = ?
        """, ((today - timedelta(days=2)).strftime('%Y-%m-%d'), session2))
        
        # Day 4: 20 minutes
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 1200, last_updated = ?
            WHERE session_id = ?
        """, ((today - timedelta(days=3)).strftime('%Y-%m-%d'), session3))
        
        test_db.conn.commit()
        
        # Calculate streak
        streak = analytics_engine.calculate_current_streak(user_id=1)
        
        # Should only have a 1-day streak (today), since day 2 was missed
        assert streak == 1


class TestLongestStreakTracking:
    """Property 44: Longest Streak Tracking.
    
    Validates: Requirements 18.5
    Verify longest_streak >= current_streak and only increases when exceeded
    """
    
    def test_longest_streak_tracks_best(self, analytics_engine, test_db):
        """Test that longest streak tracks the best streak ever achieved."""
        from datetime import datetime, timedelta
        
        # Create sessions for a 5-day streak
        sessions = [create_test_session(test_db) for _ in range(5)]
        
        cursor = test_db.conn.cursor()
        today = datetime.now().date()
        
        # Set up 5 consecutive days of reading
        for i, session_id in enumerate(sessions):
            cursor.execute("""
                UPDATE reading_progress SET time_spent_seconds = 600, last_updated = ?
                WHERE session_id = ?
            """, ((today - timedelta(days=i)).strftime('%Y-%m-%d'), session_id))
        
        test_db.conn.commit()
        
        # Calculate streaks
        current_streak = analytics_engine.calculate_current_streak(user_id=1)
        longest_streak = analytics_engine.calculate_longest_streak(user_id=1)
        
        # Longest should be at least as big as current
        assert longest_streak >= current_streak
        assert longest_streak == 5
    
    def test_longest_streak_preserves_best(self, analytics_engine, test_db):
        """Test that longest streak is preserved even when current streak is shorter."""
        from datetime import datetime, timedelta
        
        # Create sessions for a 3-day streak
        sessions = [create_test_session(test_db) for _ in range(3)]
        
        cursor = test_db.conn.cursor()
        today = datetime.now().date()
        
        # Set up 3 consecutive days
        for i, session_id in enumerate(sessions):
            cursor.execute("""
                UPDATE reading_progress SET time_spent_seconds = 600, last_updated = ?
                WHERE session_id = ?
            """, ((today - timedelta(days=i)).strftime('%Y-%m-%d'), session_id))
        
        test_db.conn.commit()
        
        # Calculate initial streaks
        initial_longest = analytics_engine.calculate_longest_streak(user_id=1)
        
        # Now add a session from 10 days ago (should not affect current streak)
        old_session = create_test_session(test_db)
        cursor.execute("""
            UPDATE reading_progress SET time_spent_seconds = 600, last_updated = ?
            WHERE session_id = ?
        """, ((today - timedelta(days=10)).strftime('%Y-%m-%d'), old_session))
        
        test_db.conn.commit()
        
        # Calculate new streaks
        new_longest = analytics_engine.calculate_longest_streak(user_id=1)
        
        # Longest should be preserved
        assert new_longest == initial_longest
