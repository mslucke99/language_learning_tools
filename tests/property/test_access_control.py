"""
Property-based tests for Immersive Reading Mode access control enforcement.

These tests verify that users cannot access reading sessions owned by other users,
ensuring privacy and data isolation between users.

Property 4: Access Control Enforcement
- Validates: Requirements 2.3, 2.5
- Verifies users cannot access other users' sessions
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.core.database import FlashcardDatabase
from src.features.reader.content_manager import ContentManager


class TestAccessControlEnforcement:
    """
    Property 4: Access Control Enforcement
    
    This property ensures that reading sessions are strictly isolated by user_id.
    A user can only access their own reading sessions, and any attempt to access
    another user's session must return None (unauthorized access).
    
    This is critical for:
    - Privacy: Users' imported content must remain private
    - Legal compliance: Prevents accidental sharing of copyrighted material
    - Data security: Enforces proper authorization checks
    
    The property is tested across various scenarios:
    - Single user with multiple sessions
    - Multiple users with their own sessions
    - Attempts to access non-existent sessions
    - Attempts to access sessions owned by other users
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

    def test_user_can_access_own_session(self, content_manager, db):
        """
        Test that a user can access their own reading session.
        
        Operation: User creates session, then retrieves it
        Expected: Session is returned successfully
        """
        # User 1 creates a session
        session_id = content_manager.import_from_paste(
            content='Test content for user 1. ' * 20,
            title='User 1 Article',
            language='en',
            user_attestation=True,
            user_id=1
        )
        
        # User 1 retrieves their own session
        session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Verify session is returned
        assert session is not None, "User should be able to access their own session"
        assert session['id'] == session_id
        assert session['user_id'] == 1
        assert session['title'] == 'User 1 Article'

    def test_user_cannot_access_other_users_session(self, content_manager, db):
        """
        Test that a user cannot access another user's reading session.
        
        Operation: User 1 creates session, User 2 attempts to access it
        Expected: Access denied (returns None)
        """
        # User 1 creates a session
        session_id = content_manager.import_from_paste(
            content='Private content for user 1. ' * 20,
            title='User 1 Private Article',
            language='en',
            user_attestation=True,
            user_id=1
        )
        
        # User 2 attempts to access User 1's session
        session = content_manager.get_reading_session(session_id, user_id=2)
        
        # Verify access is denied
        assert session is None, \
            "User 2 should NOT be able to access User 1's session"

    def test_multiple_users_cannot_access_each_others_sessions(self, content_manager, db):
        """
        Test that multiple users cannot access each other's sessions.
        
        Operation: Multiple users create sessions, each tries to access others'
        Expected: Each user can only access their own sessions
        """
        # Create sessions for users 1, 2, and 3
        sessions = {}
        for user_id in [1, 2, 3]:
            session_id = content_manager.import_from_paste(
                content=f'Content for user {user_id}. ' * 20,
                title=f'User {user_id} Article',
                language='en',
                user_attestation=True,
                user_id=user_id
            )
            sessions[user_id] = session_id
        
        # Verify each user can access their own session
        for user_id, session_id in sessions.items():
            session = content_manager.get_reading_session(session_id, user_id=user_id)
            assert session is not None, \
                f"User {user_id} should be able to access their own session"
            assert session['user_id'] == user_id
        
        # Verify users cannot access other users' sessions
        for owner_id, session_id in sessions.items():
            for requester_id in [1, 2, 3]:
                if requester_id != owner_id:
                    session = content_manager.get_reading_session(
                        session_id, 
                        user_id=requester_id
                    )
                    assert session is None, \
                        f"User {requester_id} should NOT be able to access " \
                        f"User {owner_id}'s session"

    def test_access_control_with_nonexistent_session(self, content_manager, db):
        """
        Test that accessing a non-existent session returns None.
        
        Operation: Attempt to access session ID that doesn't exist
        Expected: Returns None (not found)
        """
        # Attempt to access non-existent session
        session = content_manager.get_reading_session(session_id=99999, user_id=1)
        
        # Verify None is returned
        assert session is None, \
            "Accessing non-existent session should return None"

    def test_access_control_after_session_deletion(self, content_manager, db):
        """
        Test that access control works correctly after session deletion.
        
        Operation: Create session, delete it, attempt to access
        Expected: Returns None (session no longer exists)
        """
        # User 1 creates a session
        session_id = content_manager.import_from_paste(
            content='Temporary content. ' * 20,
            title='Temporary Article',
            language='en',
            user_attestation=True,
            user_id=1
        )
        
        # Verify user can access it
        session = content_manager.get_reading_session(session_id, user_id=1)
        assert session is not None
        
        # Delete the session
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM reading_sessions WHERE id = ?", (session_id,))
        db.conn.commit()
        
        # Attempt to access deleted session
        session = content_manager.get_reading_session(session_id, user_id=1)
        
        # Verify None is returned
        assert session is None, \
            "Accessing deleted session should return None"

    @given(
        owner_user_id=st.integers(min_value=1, max_value=100),
        requester_user_id=st.integers(min_value=1, max_value=100),
        title=st.text(min_size=1, max_size=100),
        content=st.text(min_size=100, max_size=1000).filter(lambda x: len(x.strip()) >= 100)
    )
    @settings(max_examples=50, deadline=None)
    def test_access_control_property_based(
        self,
        owner_user_id,
        requester_user_id,
        title,
        content
    ):
        """
        Property test: Users can only access their own sessions.
        
        For ANY owner_user_id and requester_user_id:
        - If owner_user_id == requester_user_id: access granted
        - If owner_user_id != requester_user_id: access denied
        
        This property must hold for all possible user ID combinations.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and manager
            db = FlashcardDatabase(db_name=temp_db_path)
            content_manager = ContentManager(db)
            
            # Owner creates a session
            session_id = content_manager.import_from_paste(
                content=content,
                title=title,
                language='en',
                user_attestation=True,
                user_id=owner_user_id
            )
            
            # Requester attempts to access the session
            session = content_manager.get_reading_session(
                session_id,
                user_id=requester_user_id
            )
            
            # Verify access control property
            if owner_user_id == requester_user_id:
                # Same user: access should be granted
                assert session is not None, \
                    f"User {requester_user_id} should be able to access their own session"
                assert session['id'] == session_id
                assert session['user_id'] == owner_user_id
            else:
                # Different user: access should be denied
                assert session is None, \
                    f"User {requester_user_id} should NOT be able to access " \
                    f"User {owner_user_id}'s session"
        
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

    def test_access_control_with_multiple_sessions_per_user(self, content_manager, db):
        """
        Test access control when users have multiple sessions.
        
        Operation: Each user creates multiple sessions
        Expected: Each user can access all their own sessions, none from others
        """
        # Create multiple sessions for each user
        user_sessions = {
            1: [],
            2: [],
            3: []
        }
        
        for user_id in [1, 2, 3]:
            for i in range(3):
                session_id = content_manager.import_from_paste(
                    content=f'Content for user {user_id}, session {i}. ' * 20,
                    title=f'User {user_id} Article {i}',
                    language='en',
                    user_attestation=True,
                    user_id=user_id
                )
                user_sessions[user_id].append(session_id)
        
        # Verify each user can access all their own sessions
        for user_id, session_ids in user_sessions.items():
            for session_id in session_ids:
                session = content_manager.get_reading_session(session_id, user_id=user_id)
                assert session is not None, \
                    f"User {user_id} should be able to access their session {session_id}"
                assert session['user_id'] == user_id
        
        # Verify users cannot access any sessions from other users
        for owner_id, session_ids in user_sessions.items():
            for requester_id in [1, 2, 3]:
                if requester_id != owner_id:
                    for session_id in session_ids:
                        session = content_manager.get_reading_session(
                            session_id,
                            user_id=requester_id
                        )
                        assert session is None, \
                            f"User {requester_id} should NOT be able to access " \
                            f"User {owner_id}'s session {session_id}"

    def test_access_control_preserves_session_data_integrity(self, content_manager, db):
        """
        Test that access control doesn't modify session data.
        
        Operation: Multiple access attempts (authorized and unauthorized)
        Expected: Session data remains unchanged
        """
        # User 1 creates a session
        session_id = content_manager.import_from_paste(
            content='Original content that should not change. ' * 20,
            title='Original Title',
            language='en',
            user_attestation=True,
            user_id=1
        )
        
        # Get original session data
        original_session = content_manager.get_reading_session(session_id, user_id=1)
        assert original_session is not None
        
        # Multiple unauthorized access attempts by other users
        for user_id in [2, 3, 4, 5]:
            session = content_manager.get_reading_session(session_id, user_id=user_id)
            assert session is None
        
        # Multiple authorized access attempts by owner
        for _ in range(5):
            session = content_manager.get_reading_session(session_id, user_id=1)
            assert session is not None
        
        # Verify session data is unchanged
        final_session = content_manager.get_reading_session(session_id, user_id=1)
        assert final_session is not None
        assert final_session['title'] == original_session['title']
        assert final_session['content'] == original_session['content']
        assert final_session['user_id'] == original_session['user_id']

    def test_access_control_with_user_id_zero(self, content_manager, db):
        """
        Test access control with edge case user_id = 0.
        
        Operation: Create session with user_id=0, test access
        Expected: Access control works correctly for user_id=0
        """
        # Create session with user_id=0 (edge case)
        session_id = content_manager.import_from_paste(
            content='Content for user 0. ' * 20,
            title='User 0 Article',
            language='en',
            user_attestation=True,
            user_id=0
        )
        
        # User 0 should be able to access their session
        session = content_manager.get_reading_session(session_id, user_id=0)
        assert session is not None
        assert session['user_id'] == 0
        
        # Other users should not be able to access it
        for user_id in [1, 2, 3]:
            session = content_manager.get_reading_session(session_id, user_id=user_id)
            assert session is None, \
                f"User {user_id} should NOT be able to access User 0's session"

    def test_access_control_with_large_user_ids(self, content_manager, db):
        """
        Test access control with large user IDs.
        
        Operation: Create sessions with large user IDs
        Expected: Access control works correctly regardless of user ID magnitude
        """
        large_user_ids = [1000, 10000, 100000, 999999]
        sessions = {}
        
        # Create sessions for large user IDs
        for user_id in large_user_ids:
            session_id = content_manager.import_from_paste(
                content=f'Content for user {user_id}. ' * 20,
                title=f'User {user_id} Article',
                language='en',
                user_attestation=True,
                user_id=user_id
            )
            sessions[user_id] = session_id
        
        # Verify each user can access their own session
        for user_id, session_id in sessions.items():
            session = content_manager.get_reading_session(session_id, user_id=user_id)
            assert session is not None
            assert session['user_id'] == user_id
        
        # Verify users cannot access other users' sessions
        for owner_id, session_id in sessions.items():
            for requester_id in large_user_ids:
                if requester_id != owner_id:
                    session = content_manager.get_reading_session(
                        session_id,
                        user_id=requester_id
                    )
                    assert session is None

    def test_access_control_comprehensive_matrix(self, content_manager, db):
        """
        Comprehensive test: Create sessions for multiple users and verify
        complete access control matrix.
        
        Operation: N users create M sessions each, test all access combinations
        Expected: Each user can only access their own N sessions
        """
        num_users = 5
        sessions_per_user = 3
        
        # Create sessions
        all_sessions = {}
        for user_id in range(1, num_users + 1):
            all_sessions[user_id] = []
            for session_num in range(sessions_per_user):
                session_id = content_manager.import_from_paste(
                    content=f'User {user_id} session {session_num} content. ' * 20,
                    title=f'U{user_id}S{session_num}',
                    language='en',
                    user_attestation=True,
                    user_id=user_id
                )
                all_sessions[user_id].append(session_id)
        
        # Test complete access control matrix
        access_matrix = []
        for owner_id in range(1, num_users + 1):
            for session_id in all_sessions[owner_id]:
                for requester_id in range(1, num_users + 1):
                    session = content_manager.get_reading_session(
                        session_id,
                        user_id=requester_id
                    )
                    
                    if owner_id == requester_id:
                        # Should have access
                        assert session is not None, \
                            f"Access matrix violation: User {requester_id} should " \
                            f"access their own session {session_id}"
                        access_matrix.append((owner_id, session_id, requester_id, True))
                    else:
                        # Should NOT have access
                        assert session is None, \
                            f"Access matrix violation: User {requester_id} should NOT " \
                            f"access User {owner_id}'s session {session_id}"
                        access_matrix.append((owner_id, session_id, requester_id, False))
        
        # Verify matrix completeness
        expected_entries = num_users * sessions_per_user * num_users
        assert len(access_matrix) == expected_entries, \
            f"Access matrix should have {expected_entries} entries"
        
        # Count authorized vs unauthorized accesses
        authorized = sum(1 for _, _, _, granted in access_matrix if granted)
        unauthorized = sum(1 for _, _, _, granted in access_matrix if not granted)
        
        expected_authorized = num_users * sessions_per_user
        expected_unauthorized = num_users * sessions_per_user * (num_users - 1)
        
        assert authorized == expected_authorized, \
            f"Expected {expected_authorized} authorized accesses, got {authorized}"
        assert unauthorized == expected_unauthorized, \
            f"Expected {expected_unauthorized} unauthorized accesses, got {unauthorized}"
