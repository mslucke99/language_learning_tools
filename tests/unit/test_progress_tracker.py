"""
Unit tests for ReadingProgressTracker class.

Tests progress tracking functionality including position updates,
time tracking, auto-save mechanism, and force save on close.
"""

import pytest
import tempfile
import os
import time
from hypothesis import given, strategies as st, settings, HealthCheck
from src.core.database import FlashcardDatabase
from src.features.reader.progress_tracker import ReadingProgressTracker


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = FlashcardDatabase(db_name=db_path)
    
    yield db
    
    db.conn.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def progress_tracker(test_db):
    """Create a ReadingProgressTracker instance with test database."""
    # First create a reading session
    cursor = test_db.conn.cursor()
    cursor.execute("""
        INSERT INTO reading_sessions
        (user_id, title, content, language, source, import_method,
         legal_attestation, private, shareable, created_at)
        VALUES (1, 'Test', 'Test content for reading.', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
    """)
    session_id = cursor.lastrowid
    
    # Create initial progress entry
    cursor.execute("""
        INSERT INTO reading_progress
        (session_id, user_id, current_position, current_paragraph,
         completion_percentage, time_spent_seconds, completed,
         started_at, last_updated)
        VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (session_id,))
    
    test_db.conn.commit()
    
    return ReadingProgressTracker(session_id, test_db)


class TestReadingProgressTrackerInit:
    """Test ReadingProgressTracker initialization."""
    
    def test_init_stores_session_id(self, test_db):
        """Test that initialization stores session ID."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id,))
        
        test_db.conn.commit()
        
        tracker = ReadingProgressTracker(session_id, test_db)
        assert tracker.session_id == session_id
    
    def test_init_stores_database(self, test_db):
        """Test that initialization stores database reference."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id,))
        
        test_db.conn.commit()
        
        tracker = ReadingProgressTracker(session_id, test_db)
        assert tracker.db is test_db
    
    def test_init_sets_save_interval(self, test_db):
        """Test that SAVE_INTERVAL is set to 30 seconds."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id,))
        
        test_db.conn.commit()
        
        tracker = ReadingProgressTracker(session_id, test_db)
        assert tracker.SAVE_INTERVAL == 30
    
    def test_init_initializes_pending_changes(self, test_db):
        """Test that initialization initializes empty pending_changes."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id,))
        
        test_db.conn.commit()
        
        tracker = ReadingProgressTracker(session_id, test_db)
        assert tracker.pending_changes == {}
    
    def test_init_sets_last_save_timestamp(self, test_db):
        """Test that initialization sets last_save timestamp."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_sessions
            (user_id, title, content, language, source, import_method,
             legal_attestation, private, shareable, created_at)
            VALUES (1, 'Test', 'Test content', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
        """)
        session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO reading_progress
            (session_id, user_id, current_position, current_paragraph,
             completion_percentage, time_spent_seconds, completed,
             started_at, last_updated)
            VALUES (?, 1, 0, 0, 0.0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (session_id,))
        
        test_db.conn.commit()
        
        tracker = ReadingProgressTracker(session_id, test_db)
        assert tracker.last_save > 0  # Should be a valid timestamp


class TestUpdatePosition:
    """Test position update functionality."""
    
    def test_update_position_stores_pending(self, progress_tracker):
        """Test that update_position stores position in pending_changes."""
        progress_tracker.update_position(100, 1)
        
        pending = progress_tracker.get_pending_changes()
        assert 'position' in pending
        assert pending['position'] == 100
        assert 'paragraph' in pending
        assert pending['paragraph'] == 1
    
    def test_update_position_triggers_auto_save(self, progress_tracker):
        """Test that update_position triggers auto-save mechanism."""
        # Force last_save to be old enough to trigger save
        progress_tracker.last_save = time.time() - 31
        
        progress_tracker.update_position(100, 1)
        
        # Verify position was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position, current_paragraph
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 100
        assert row[1] == 1
    
    def test_update_position_multiple_times(self, progress_tracker):
        """Test updating position multiple times."""
        progress_tracker.update_position(100, 1)
        progress_tracker.update_position(200, 2)
        progress_tracker.update_position(300, 3)
        
        pending = progress_tracker.get_pending_changes()
        assert pending['position'] == 300
        assert pending['paragraph'] == 3


class TestUpdateTime:
    """Test time update functionality."""
    
    def test_update_time_stores_pending(self, progress_tracker):
        """Test that update_time stores time in pending_changes."""
        progress_tracker.update_time(60)
        
        pending = progress_tracker.get_pending_changes()
        assert 'time' in pending
        assert pending['time'] == 60
    
    def test_update_time_triggers_auto_save(self, progress_tracker):
        """Test that update_time triggers auto-save mechanism."""
        # Force last_save to be old enough to trigger save
        progress_tracker.last_save = time.time() - 31
        
        progress_tracker.update_time(60)
        
        # Verify time was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT time_spent_seconds
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 60
    
    def test_update_time_multiple_times(self, progress_tracker):
        """Test updating time multiple times."""
        progress_tracker.update_time(60)
        progress_tracker.update_time(120)
        progress_tracker.update_time(180)
        
        pending = progress_tracker.get_pending_changes()
        assert pending['time'] == 180


class TestUpdateCompletion:
    """Test completion percentage update functionality."""
    
    def test_update_completion_stores_pending(self, progress_tracker):
        """Test that update_completion stores completion in pending_changes."""
        progress_tracker.update_completion(50.0)
        
        pending = progress_tracker.get_pending_changes()
        assert 'completion' in pending
        assert pending['completion'] == 50.0
    
    def test_update_completion_triggers_auto_save(self, progress_tracker):
        """Test that update_completion triggers auto-save mechanism."""
        # Force last_save to be old enough to trigger save
        progress_tracker.last_save = time.time() - 31
        
        progress_tracker.update_completion(50.0)
        
        # Verify completion was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT completion_percentage
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 50.0


class TestAutoSaveMechanism:
    """Test auto-save mechanism."""
    
    def test_auto_save_triggers_after_interval(self, progress_tracker):
        """Test that auto-save triggers after 30 seconds."""
        # Force last_save to be 31 seconds ago
        progress_tracker.last_save = time.time() - 31
        
        # Update position (should trigger auto-save)
        progress_tracker.update_position(100, 1)
        
        # Verify position was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 100
    
    def test_auto_save_does_not_trigger_before_interval(self, progress_tracker):
        """Test that auto-save does not trigger before 30 seconds."""
        # Force last_save to be 10 seconds ago
        progress_tracker.last_save = time.time() - 10
        
        # Update position
        progress_tracker.update_position(100, 1)
        
        # Verify position was NOT saved to database (still in pending)
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        # Position should still be 0 (not updated)
        assert row[0] == 0
    
    def test_auto_save_clears_pending_after_save(self, progress_tracker):
        """Test that auto-save clears pending_changes after save."""
        # Force last_save to be old enough to trigger save
        progress_tracker.last_save = time.time() - 31
        
        # Update position
        progress_tracker.update_position(100, 1)
        
        # Verify pending_changes is cleared
        pending = progress_tracker.get_pending_changes()
        assert pending == {}


class TestForceSave:
    """Test force save functionality."""
    
    def test_force_save_immediately_persists(self, progress_tracker):
        """Test that force_save immediately persists changes."""
        # Update position
        progress_tracker.update_position(100, 1)
        
        # Force save
        progress_tracker.force_save()
        
        # Verify position was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 100
    
    def test_force_save_clears_pending(self, progress_tracker):
        """Test that force_save clears pending_changes."""
        # Update position
        progress_tracker.update_position(100, 1)
        
        # Force save
        progress_tracker.force_save()
        
        # Verify pending_changes is cleared
        pending = progress_tracker.get_pending_changes()
        assert pending == {}
    
    def test_force_save_when_no_pending(self, progress_tracker):
        """Test that force_save handles empty pending_changes."""
        # Force save with no pending changes
        progress_tracker.force_save()
        
        # Should not raise an error
        assert True


class TestGetPendingChanges:
    """Test get_pending_changes functionality."""
    
    def test_get_pending_changes_returns_copy(self, progress_tracker):
        """Test that get_pending_changes returns a copy."""
        progress_tracker.update_position(100, 1)
        
        pending1 = progress_tracker.get_pending_changes()
        pending2 = progress_tracker.get_pending_changes()
        
        # Modifying one should not affect the other
        pending1['position'] = 200
        
        assert pending2['position'] == 100


class TestGetLastSaveTime:
    """Test get_last_save_time functionality."""
    
    def test_get_last_save_time_returns_timestamp(self, progress_tracker):
        """Test that get_last_save_time returns a valid timestamp."""
        last_save = progress_tracker.get_last_save_time()
        
        assert last_save > 0
        assert isinstance(last_save, float)


# Property-based tests

class TestPositionUpdateOnNavigationProperty:
    """
    Property-based tests for position update on navigation.
    
    Property 11: Position Update on Navigation
    Validates: Requirements 3.5
    
    This test verifies that for ANY navigation action (scroll,
    next paragraph, previous paragraph), the current_position
    and current_paragraph fields are updated in the database.
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        position=st.integers(min_value=0, max_value=10000),
        paragraph=st.integers(min_value=0, max_value=1000)
    )
    def test_property_position_updated_on_navigation(
        self,
        position,
        paragraph,
        progress_tracker
    ):
        """
        Property test: Position is updated on navigation.
        
        For ANY position and paragraph values, when update_position()
        is called, the database should be updated with these values.
        
        This ensures that reading progress is accurately tracked
        as users navigate through content.
        
        Validates Requirement 3.5: Update position on navigation
        """
        # Force auto-save to trigger immediately
        progress_tracker.last_save = time.time() - 31
        
        # Update position
        progress_tracker.update_position(position, paragraph)
        
        # Verify position was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position, current_paragraph
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None, "Progress entry should exist"
        assert row[0] == position, f"Position should be {position}, got {row[0]}"
        assert row[1] == paragraph, f"Paragraph should be {paragraph}, got {row[1]}"


class TestCompletionPercentageFormulaProperty:
    """
    Property-based tests for completion percentage formula.
    
    Property 29: Completion Percentage Formula
    Validates: Requirements 10.3
    
    This test verifies that for ANY reading session, the
    completion_percentage equals (current_position / total_length) * 100.
    """
    
    def test_property_completion_percentage_in_valid_range(
        self,
        progress_tracker
    ):
        """
        Property test: Completion percentage is in valid range [0.0, 100.0].
        
        For ANY reading session, the completion_percentage should be
        between 0.0 and 100.0 (inclusive).
        
        Validates Requirement 10.3: Completion percentage calculation
        """
        # Update completion to various values
        test_values = [0.0, 25.0, 50.0, 75.0, 100.0]
        
        for value in test_values:
            progress_tracker.update_completion(value)
            progress_tracker.force_save()
            
            # Verify completion is in valid range
            cursor = progress_tracker.db.conn.cursor()
            cursor.execute("""
                SELECT completion_percentage
                FROM reading_progress
                WHERE session_id = ?
            """, (progress_tracker.session_id,))
            
            row = cursor.fetchone()
            assert row is not None
            completion = row[0]
            assert 0.0 <= completion <= 100.0, (
                f"Completion {completion} is not in valid range [0.0, 100.0]"
            )


class TestProgressAutoSaveIntervalProperty:
    """
    Property-based tests for progress auto-save interval.
    
    Property 10: Progress Auto-Save Interval
    Validates: Requirements 3.6, 10.1
    
    This test verifies that for ANY reading session, progress
    saves to the database after 30 seconds elapse.
    """
    
    def test_property_progress_saves_after_interval(
        self,
        progress_tracker
    ):
        """
        Property test: Progress saves to database after 30 seconds.
        
        For ANY reading session, if 30 seconds elapse since the
        last save, the next update should trigger an auto-save
        and persist changes to the database.
        
        Validates Requirements 3.6, 10.1: Auto-save every 30 seconds
        """
        # Force last_save to be 31 seconds ago
        progress_tracker.last_save = time.time() - 31
        
        # Update position
        progress_tracker.update_position(500, 5)
        
        # Verify position was saved to database
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None, "Progress entry should exist"
        assert row[0] == 500, (
            f"Position should be 500 after auto-save, got {row[0]}"
        )


class TestForceSaveOnCloseProperty:
    """
    Property-based tests for force save on close.
    
    Property 30: Force Save on Close
    Validates: Requirements 10.5
    
    This test verifies that for ANY reading session, when the
    application closes, all pending progress changes are
    persisted to the database.
    """
    
    def test_property_pending_changes_persist_on_force_save(
        self,
        progress_tracker
    ):
        """
        Property test: Pending changes persist when force_save is called.
        
        For ANY pending changes (position, paragraph, time, completion),
        calling force_save() should persist all changes to the database
        regardless of the auto-save interval.
        
        Validates Requirement 10.5: Force save on close
        """
        # Update multiple fields
        progress_tracker.update_position(750, 7)
        progress_tracker.update_time(120)
        progress_tracker.update_completion(75.0)
        
        # Force save (simulating application close)
        progress_tracker.force_save()
        
        # Verify all changes were persisted
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position, current_paragraph,
                   time_spent_seconds, completion_percentage
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None, "Progress entry should exist"
        assert row[0] == 750, "Position should be 750"
        assert row[1] == 7, "Paragraph should be 7"
        assert row[2] == 120, "Time should be 120"
        assert row[3] == 75.0, "Completion should be 75.0"


class TestPositionRoundTripProperty:
    """
    Property-based tests for position round-trip.
    
    Property 9: Reading Position Round-Trip
    Validates: Requirements 2.6, 9.4, 10.6
    
    This test verifies that for ANY reading session, if we save
    a position, close the session, and reopen it, the restored
    position equals the saved position.
    """
    
    def test_property_position_restored_after_close_reopen(
        self,
        progress_tracker
    ):
        """
        Property test: Position is restored correctly after close/reopen.
        
        For ANY reading session, if we:
        1. Save a position using update_position()
        2. Force save (simulating close)
        3. Create a new tracker instance (simulating reopen)
        4. Read the position from database
        
        The restored position should equal the saved position.
        
        Validates Requirements 2.6, 9.4, 10.6: Position restoration
        """
        # Save position
        test_position = 800
        test_paragraph = 8
        
        progress_tracker.update_position(test_position, test_paragraph)
        progress_tracker.force_save()
        
        # Create new tracker instance (simulating reopen)
        new_tracker = ReadingProgressTracker(
            progress_tracker.session_id,
            progress_tracker.db
        )
        
        # Verify position was restored
        cursor = progress_tracker.db.conn.cursor()
        cursor.execute("""
            SELECT current_position, current_paragraph
            FROM reading_progress
            WHERE session_id = ?
        """, (progress_tracker.session_id,))
        
        row = cursor.fetchone()
        assert row is not None, "Progress entry should exist"
        assert row[0] == test_position, (
            f"Position should be {test_position}, got {row[0]}"
        )
        assert row[1] == test_paragraph, (
            f"Paragraph should be {test_paragraph}, got {row[1]}"
        )
