"""
Property-based tests for Immersive Reading Mode reading position round-trip.

These tests verify that reading positions are correctly saved and restored
when a user closes and reopens a reading session, ensuring continuity of
the reading experience.

Property 9: Reading Position Round-Trip
- Validates: Requirements 2.6, 9.4, 10.6
- Verify saved position equals restored position after close/reopen
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings
from src.core.database import FlashcardDatabase
from src.features.reader.content_manager import ContentManager


class TestReadingPositionRoundTrip:
    """
    Property 9: Reading Position Round-Trip
    
    This property ensures that reading progress is correctly persisted and restored.
    When a user:
    1. Opens a reading session
    2. Reads to a specific position
    3. Saves their progress
    4. Closes the session
    5. Reopens the session
    
    Then the restored position must EXACTLY match the saved position.
    
    This is critical for:
    - User experience: Users expect to resume exactly where they left off
    - Data integrity: Progress tracking must be reliable
    - Trust: Users must trust that their progress won't be lost
    
    The property is tested across various scenarios:
    - Different positions within content (beginning, middle, end)
    - Different completion percentages
    - Different time spent values
    - Multiple save/restore cycles
    - Multiple sessions with different positions
    """

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def db(self, temp_db):
        """Create a FlashcardDatabase instance."""
        database = FlashcardDatabase(db_name=temp_db)
        yield database
        database.close()

    @pytest.fixture
    def content_manager(self, db):
        """Create a ContentManager instance."""
        return ContentManager(db)

    def _create_test_session(
        self,
        content_manager: ContentManager,
        content: str,
        title: str = "Test Article",
        language: str = "en",
        user_id: int = 1
    ) -> int:
        """
        Helper method to create a test reading session.
        
        Args:
            content_manager: ContentManager instance
            content: Text content for the session
            title: Session title
            language: Language code
            user_id: User ID
            
        Returns:
            session_id: ID of created session
        """
        return content_manager.import_from_paste(
            content=content,
            title=title,
            language=language,
            user_attestation=True,
            user_id=user_id
        )

    def test_basic_position_round_trip(self, content_manager, db):
        """
        Test basic round-trip: save position, close, reopen, verify position.
        
        Operation: Create session, update position, retrieve session
        Expected: Retrieved position matches saved position
        """
        # Create a reading session
        content = "This is a test article. " * 50  # ~1200 characters
        session_id = self._create_test_session(content_manager, content)
        
        # Simulate reading to position 500
        saved_position = 500
        saved_completion = 41.67  # ~500/1200 * 100
        saved_time = 120  # 2 minutes
        
        # Save progress
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=saved_position,
            completion_percentage=saved_completion,
            time_spent_seconds=saved_time
        )
        assert success, "Progress update should succeed"
        
        # Simulate closing and reopening: retrieve the session
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Verify position was restored correctly
        assert restored_session is not None, "Session should be retrievable"
        assert restored_session['current_position'] == saved_position, \
            f"Position mismatch: saved {saved_position}, restored {restored_session['current_position']}"
        assert restored_session['completion_percentage'] == saved_completion, \
            f"Completion mismatch: saved {saved_completion}, restored {restored_session['completion_percentage']}"
        assert restored_session['time_spent_seconds'] == saved_time, \
            f"Time mismatch: saved {saved_time}, restored {restored_session['time_spent_seconds']}"

    def test_position_round_trip_at_beginning(self, content_manager, db):
        """
        Test round-trip when position is at the beginning (position 0).
        
        Operation: Save position 0, retrieve session
        Expected: Position 0 is correctly restored
        """
        content = "Test content. " * 100
        session_id = self._create_test_session(content_manager, content)
        
        # Save position at beginning
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=0,
            completion_percentage=0.0,
            time_spent_seconds=0
        )
        assert success
        
        # Retrieve and verify
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        assert restored_session['current_position'] == 0
        assert restored_session['completion_percentage'] == 0.0
        assert restored_session['time_spent_seconds'] == 0

    def test_position_round_trip_at_end(self, content_manager, db):
        """
        Test round-trip when position is at the end (100% completion).
        
        Operation: Save position at end of content, retrieve session
        Expected: End position is correctly restored
        """
        content = "Test content. " * 100
        content_length = len(content)
        session_id = self._create_test_session(content_manager, content)
        
        # Save position at end
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=content_length,
            completion_percentage=100.0,
            time_spent_seconds=600
        )
        assert success
        
        # Retrieve and verify
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        assert restored_session['current_position'] == content_length
        assert restored_session['completion_percentage'] == 100.0
        assert restored_session['time_spent_seconds'] == 600

    def test_multiple_position_updates_round_trip(self, content_manager, db):
        """
        Test round-trip with multiple sequential position updates.
        
        Operation: Update position multiple times, verify each time
        Expected: Each update is correctly persisted and restored
        """
        content = "Test content. " * 100
        session_id = self._create_test_session(content_manager, content)
        
        # Simulate reading progress over multiple sessions
        positions = [
            (100, 10.0, 60),    # 10% after 1 minute
            (300, 30.0, 180),   # 30% after 3 minutes
            (500, 50.0, 300),   # 50% after 5 minutes
            (700, 70.0, 420),   # 70% after 7 minutes
            (900, 90.0, 540),   # 90% after 9 minutes
        ]
        
        for position, completion, time_spent in positions:
            # Save progress
            success = content_manager.update_reading_progress(
                session_id=session_id,
                current_position=position,
                completion_percentage=completion,
                time_spent_seconds=time_spent
            )
            assert success
            
            # Retrieve and verify
            restored_session = content_manager.get_reading_session(session_id, user_id=1)
            assert restored_session['current_position'] == position, \
                f"Position mismatch at {position}"
            assert restored_session['completion_percentage'] == completion, \
                f"Completion mismatch at {completion}"
            assert restored_session['time_spent_seconds'] == time_spent, \
                f"Time mismatch at {time_spent}"

    def test_position_round_trip_multiple_sessions(self, content_manager, db):
        """
        Test round-trip with multiple independent reading sessions.
        
        Operation: Create multiple sessions, save different positions for each
        Expected: Each session maintains its own independent position
        """
        # Create multiple sessions
        sessions = []
        for i in range(5):
            content = f"Content for session {i}. " * 50
            session_id = self._create_test_session(
                content_manager,
                content,
                title=f"Article {i}"
            )
            sessions.append({
                'id': session_id,
                'position': (i + 1) * 100,
                'completion': (i + 1) * 10.0,
                'time': (i + 1) * 60
            })
        
        # Save progress for each session
        for session in sessions:
            success = content_manager.update_reading_progress(
                session_id=session['id'],
                current_position=session['position'],
                completion_percentage=session['completion'],
                time_spent_seconds=session['time']
            )
            assert success
        
        # Verify each session has correct independent position
        for session in sessions:
            restored = content_manager.get_reading_session(session['id'], user_id=1)
            assert restored['current_position'] == session['position'], \
                f"Session {session['id']} position mismatch"
            assert restored['completion_percentage'] == session['completion'], \
                f"Session {session['id']} completion mismatch"
            assert restored['time_spent_seconds'] == session['time'], \
                f"Session {session['id']} time mismatch"

    def test_position_round_trip_with_paragraph_tracking(self, content_manager, db):
        """
        Test round-trip including paragraph position tracking.
        
        Operation: Save position with paragraph index, retrieve session
        Expected: Both character position and paragraph index are restored
        """
        content = "Paragraph 1 with enough content to meet minimum length requirements.\n\nParagraph 2 with more text.\n\nParagraph 3 continues.\n\nParagraph 4 ends here."
        session_id = self._create_test_session(content_manager, content)
        
        # Save progress at paragraph 2
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=30,  # Somewhere in paragraph 2
            completion_percentage=50.0,
            time_spent_seconds=120
        )
        assert success
        
        # Note: current_paragraph tracking would need to be added to update_reading_progress
        # For now, we verify that the character position is correctly restored
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        assert restored_session['current_position'] == 30

    @given(
        position=st.integers(min_value=0, max_value=10000),
        completion=st.floats(min_value=0.0, max_value=100.0),
        time_spent=st.integers(min_value=0, max_value=36000)  # Up to 10 hours
    )
    @settings(max_examples=100, deadline=None)
    def test_position_round_trip_property_based(
        self,
        position,
        completion,
        time_spent
    ):
        """
        Property test: Saved position always equals restored position.
        
        For ANY valid position, completion percentage, and time spent:
        - Save the progress
        - Retrieve the session
        - Verify restored values match saved values EXACTLY
        
        This property must hold for all possible progress states.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and manager
            db = FlashcardDatabase(db_name=temp_db_path)
            content_manager = ContentManager(db)
            
            # Create a session with content long enough for any position
            content = "Test content. " * 1000  # ~14000 characters
            session_id = content_manager.import_from_paste(
                content=content,
                title="Property Test Article",
                language="en",
                user_attestation=True,
                user_id=1
            )
            
            # Ensure position doesn't exceed content length
            content_length = len(content)
            if position > content_length:
                position = content_length
            
            # Save progress
            success = content_manager.update_reading_progress(
                session_id=session_id,
                current_position=position,
                completion_percentage=completion,
                time_spent_seconds=time_spent
            )
            assert success, "Progress update should succeed"
            
            # Retrieve session (simulating close/reopen)
            restored_session = content_manager.get_reading_session(session_id, user_id=1)
            
            # Verify round-trip property: saved == restored
            assert restored_session is not None, "Session should be retrievable"
            
            assert restored_session['current_position'] == position, \
                f"Position round-trip failed: saved {position}, restored {restored_session['current_position']}"
            
            assert restored_session['completion_percentage'] == completion, \
                f"Completion round-trip failed: saved {completion}, restored {restored_session['completion_percentage']}"
            
            assert restored_session['time_spent_seconds'] == time_spent, \
                f"Time round-trip failed: saved {time_spent}, restored {restored_session['time_spent_seconds']}"
        
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                # On Windows, file might still be locked - ignore cleanup error
                pass

    def test_position_round_trip_after_database_reconnect(self, temp_db):
        """
        Test round-trip after closing and reopening database connection.
        
        Operation: Save progress, close DB, reopen DB, retrieve session
        Expected: Position is correctly restored even after DB reconnect
        
        This simulates the real-world scenario where the application
        is completely closed and reopened.
        """
        # Create session and save progress
        db1 = FlashcardDatabase(db_name=temp_db)
        content_manager1 = ContentManager(db1)
        
        content = "Test content for database reconnect. " * 100
        session_id = content_manager1.import_from_paste(
            content=content,
            title="Reconnect Test",
            language="en",
            user_attestation=True,
            user_id=1
        )
        
        saved_position = 750
        saved_completion = 50.0
        saved_time = 300
        
        success = content_manager1.update_reading_progress(
            session_id=session_id,
            current_position=saved_position,
            completion_percentage=saved_completion,
            time_spent_seconds=saved_time
        )
        assert success
        
        # Close database connection (simulating app close)
        db1.close()
        
        # Reopen database connection (simulating app reopen)
        db2 = FlashcardDatabase(db_name=temp_db)
        content_manager2 = ContentManager(db2)
        
        # Retrieve session with new connection
        restored_session = content_manager2.get_reading_session(session_id, user_id=1)
        
        # Verify position was persisted across connection close/reopen
        assert restored_session is not None
        assert restored_session['current_position'] == saved_position
        assert restored_session['completion_percentage'] == saved_completion
        assert restored_session['time_spent_seconds'] == saved_time
        
        # Cleanup
        db2.close()

    def test_position_round_trip_with_zero_values(self, content_manager, db):
        """
        Test round-trip with edge case: all zero values.
        
        Operation: Save progress with position=0, completion=0, time=0
        Expected: Zero values are correctly restored (not treated as NULL)
        """
        content = "Test content. " * 100
        session_id = self._create_test_session(content_manager, content)
        
        # Save all-zero progress
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=0,
            completion_percentage=0.0,
            time_spent_seconds=0
        )
        assert success
        
        # Retrieve and verify zeros are preserved
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        assert restored_session['current_position'] == 0
        assert restored_session['completion_percentage'] == 0.0
        assert restored_session['time_spent_seconds'] == 0

    def test_position_round_trip_preserves_other_session_data(self, content_manager, db):
        """
        Test that position updates don't corrupt other session data.
        
        Operation: Save progress, verify other session fields unchanged
        Expected: Only progress fields are updated, other data intact
        """
        content = "Test content. " * 100
        title = "Original Title"
        language = "ko"
        
        session_id = self._create_test_session(
            content_manager,
            content,
            title=title,
            language=language
        )
        
        # Get original session data
        original_session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Update progress
        content_manager.update_reading_progress(
            session_id=session_id,
            current_position=500,
            completion_percentage=50.0,
            time_spent_seconds=300
        )
        
        # Retrieve updated session
        updated_session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Verify non-progress fields are unchanged
        assert updated_session['title'] == original_session['title']
        assert updated_session['content'] == original_session['content']
        assert updated_session['language'] == original_session['language']
        assert updated_session['difficulty_score'] == original_session['difficulty_score']
        assert updated_session['word_count'] == original_session['word_count']
        
        # Verify progress fields were updated
        assert updated_session['current_position'] == 500
        assert updated_session['completion_percentage'] == 50.0
        assert updated_session['time_spent_seconds'] == 300

    def test_position_round_trip_for_different_users(self, content_manager, db):
        """
        Test that position round-trip works independently for different users.
        
        Operation: Multiple users read same content, save different positions
        Expected: Each user's position is independently maintained
        """
        content = "Shared content. " * 100
        
        # Create sessions for different users
        user_sessions = {}
        for user_id in [1, 2, 3]:
            session_id = content_manager.import_from_paste(
                content=content,
                title=f"User {user_id} Article",
                language="en",
                user_attestation=True,
                user_id=user_id
            )
            user_sessions[user_id] = {
                'id': session_id,
                'position': user_id * 200,
                'completion': user_id * 20.0,
                'time': user_id * 100
            }
        
        # Save progress for each user
        for user_id, session_data in user_sessions.items():
            success = content_manager.update_reading_progress(
                session_id=session_data['id'],
                current_position=session_data['position'],
                completion_percentage=session_data['completion'],
                time_spent_seconds=session_data['time']
            )
            assert success
        
        # Verify each user's position is independently maintained
        for user_id, session_data in user_sessions.items():
            restored = content_manager.get_reading_session(
                session_data['id'],
                user_id=user_id
            )
            assert restored['current_position'] == session_data['position']
            assert restored['completion_percentage'] == session_data['completion']
            assert restored['time_spent_seconds'] == session_data['time']

    def test_position_round_trip_idempotency(self, content_manager, db):
        """
        Test that retrieving position multiple times returns same result.
        
        Operation: Save progress once, retrieve multiple times
        Expected: All retrievals return identical position data
        """
        content = "Test content. " * 100
        session_id = self._create_test_session(content_manager, content)
        
        # Save progress
        saved_position = 600
        saved_completion = 60.0
        saved_time = 360
        
        content_manager.update_reading_progress(
            session_id=session_id,
            current_position=saved_position,
            completion_percentage=saved_completion,
            time_spent_seconds=saved_time
        )
        
        # Retrieve multiple times
        retrievals = []
        for _ in range(10):
            session = content_manager.get_reading_session(session_id, user_id=1)
            retrievals.append({
                'position': session['current_position'],
                'completion': session['completion_percentage'],
                'time': session['time_spent_seconds']
            })
        
        # Verify all retrievals are identical
        for retrieval in retrievals:
            assert retrieval['position'] == saved_position
            assert retrieval['completion'] == saved_completion
            assert retrieval['time'] == saved_time

    def test_position_round_trip_with_large_values(self, content_manager, db):
        """
        Test round-trip with large position and time values.
        
        Operation: Save progress with large values
        Expected: Large values are correctly stored and restored
        """
        # Create very long content
        content = "Test content. " * 10000  # ~140,000 characters
        session_id = self._create_test_session(content_manager, content)
        
        # Save progress with large values
        large_position = 100000
        large_time = 86400  # 24 hours in seconds
        
        success = content_manager.update_reading_progress(
            session_id=session_id,
            current_position=large_position,
            completion_percentage=71.43,  # ~100000/140000 * 100
            time_spent_seconds=large_time
        )
        assert success
        
        # Retrieve and verify
        restored_session = content_manager.get_reading_session(session_id, user_id=1)
        assert restored_session['current_position'] == large_position
        assert restored_session['time_spent_seconds'] == large_time

    def test_initial_position_before_any_updates(self, content_manager, db):
        """
        Test that newly created session has correct initial position.
        
        Operation: Create session, retrieve without any updates
        Expected: Initial position is 0, completion is 0%, time is 0
        """
        content = "Test content. " * 100
        session_id = self._create_test_session(content_manager, content)
        
        # Retrieve session immediately after creation
        session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Verify initial state
        assert session['current_position'] == 0, \
            "Initial position should be 0"
        assert session['completion_percentage'] == 0.0, \
            "Initial completion should be 0.0"
        assert session['time_spent_seconds'] == 0, \
            "Initial time should be 0"
        assert session['completed'] is False, \
            "Initial completed status should be False"
