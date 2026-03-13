"""
Property-based tests for Immersive Reading Mode privacy invariants.

These tests verify that critical privacy and legal compliance properties
are maintained across all operations on reading sessions.

Property 3: Privacy Invariant
- Validates: Requirements 2.2, 2.10
- Verifies all Reading_Sessions have private=TRUE and shareable=FALSE after any operation
"""

import sqlite3
import tempfile
import os
import pytest
from src.core.database import FlashcardDatabase


class TestPrivacyInvariant:
    """
    Property 3: Privacy Invariant
    
    This property ensures that ALL reading sessions are ALWAYS private and non-shareable,
    regardless of how they are created or modified. This is a critical legal compliance
    requirement to ensure user-imported content is never accidentally shared.
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

    def _verify_privacy_invariant(self, db: FlashcardDatabase) -> None:
        """
        Helper method to verify the privacy invariant holds.
        
        Checks that ALL reading_sessions have:
        - private = 1 (TRUE)
        - shareable = 0 (FALSE)
        
        Raises AssertionError if any session violates the invariant.
        """
        cursor = db.conn.cursor()
        
        # Check for any sessions that are not private
        cursor.execute("""
            SELECT id, title, private, shareable 
            FROM reading_sessions 
            WHERE private != 1 OR shareable != 0
        """)
        violations = cursor.fetchall()
        
        assert len(violations) == 0, (
            f"Privacy invariant violated! Found {len(violations)} session(s) "
            f"that are not private or are shareable: {violations}"
        )
        
        # Also verify all sessions have the correct values
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM reading_sessions 
            WHERE private = 1 AND shareable = 0
        """)
        compliant_sessions = cursor.fetchone()[0]
        
        assert total_sessions == compliant_sessions, (
            f"Privacy invariant violated! {total_sessions} total sessions but only "
            f"{compliant_sessions} are private and non-shareable"
        )

    def test_privacy_invariant_after_valid_insert(self, db):
        """
        Test that privacy invariant holds after inserting a valid session.
        
        Operation: INSERT with correct privacy flags
        Expected: Session is created and invariant holds
        """
        cursor = db.conn.cursor()
        
        # Insert a valid session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Test Article', 'This is test content.', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        db.conn.commit()
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_prevents_public_insert(self, db):
        """
        Test that privacy invariant prevents inserting public sessions.
        
        Operation: INSERT with private=0
        Expected: Insert fails, no sessions created
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert a public session (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Public Article', 'Content', 'en', 
                        'user_paste', 'paste', 1, 0, 0)
            """)
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify privacy invariant holds (vacuously true for empty table)
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_prevents_shareable_insert(self, db):
        """
        Test that privacy invariant prevents inserting shareable sessions.
        
        Operation: INSERT with shareable=1
        Expected: Insert fails, no sessions created
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert a shareable session (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Shareable Article', 'Content', 'en', 
                        'user_paste', 'paste', 1, 1, 1)
            """)
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_prevents_public_and_shareable_insert(self, db):
        """
        Test that privacy invariant prevents inserting public AND shareable sessions.
        
        Operation: INSERT with private=0 and shareable=1
        Expected: Insert fails, no sessions created
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert a public and shareable session (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Public Shareable Article', 'Content', 'en', 
                        'user_paste', 'paste', 1, 0, 1)
            """)
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_after_multiple_inserts(self, db):
        """
        Test that privacy invariant holds after multiple valid inserts.
        
        Operation: Multiple INSERT operations
        Expected: All sessions created with correct privacy flags
        """
        cursor = db.conn.cursor()
        
        # Insert multiple valid sessions
        sessions = [
            ('Article 1', 'Content 1', 'en'),
            ('Article 2', 'Content 2', 'ko'),
            ('Article 3', 'Content 3', 'ja'),
            ('Article 4', 'Content 4', 'es'),
            ('Article 5', 'Content 5', 'fr'),
        ]
        
        for title, content, language in sessions:
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, ?, ?, ?, 'user_paste', 'paste', 1, 1, 0)
            """, (title, content, language))
        
        db.conn.commit()
        
        # Verify all sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == len(sessions)
        
        # Verify privacy invariant holds for all sessions
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_prevents_update_to_public(self, db):
        """
        Test that privacy invariant prevents updating a session to public.
        
        Operation: UPDATE to set private=0
        Expected: Update fails, session remains private
        """
        cursor = db.conn.cursor()
        
        # Insert a valid session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Test Article', 'Content', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        db.conn.commit()
        
        # Attempt to update to public (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE reading_sessions 
                SET private = 0 
                WHERE id = ?
            """, (session_id,))
        
        # Verify session is still private
        cursor.execute("""
            SELECT private, shareable FROM reading_sessions WHERE id = ?
        """, (session_id,))
        private, shareable = cursor.fetchone()
        assert private == 1
        assert shareable == 0
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_prevents_update_to_shareable(self, db):
        """
        Test that privacy invariant prevents updating a session to shareable.
        
        Operation: UPDATE to set shareable=1
        Expected: Update fails, session remains non-shareable
        """
        cursor = db.conn.cursor()
        
        # Insert a valid session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Test Article', 'Content', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        db.conn.commit()
        
        # Attempt to update to shareable (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE reading_sessions 
                SET shareable = 1 
                WHERE id = ?
            """, (session_id,))
        
        # Verify session is still non-shareable
        cursor.execute("""
            SELECT private, shareable FROM reading_sessions WHERE id = ?
        """, (session_id,))
        private, shareable = cursor.fetchone()
        assert private == 1
        assert shareable == 0
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_allows_valid_updates(self, db):
        """
        Test that privacy invariant allows updates to other fields.
        
        Operation: UPDATE to modify title, content, etc. (not privacy flags)
        Expected: Update succeeds, privacy flags unchanged
        """
        cursor = db.conn.cursor()
        
        # Insert a valid session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Original Title', 'Original Content', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        db.conn.commit()
        
        # Update other fields (should succeed)
        cursor.execute("""
            UPDATE reading_sessions 
            SET title = 'Updated Title', 
                content = 'Updated Content',
                difficulty_score = 0.75
            WHERE id = ?
        """, (session_id,))
        db.conn.commit()
        
        # Verify updates were applied
        cursor.execute("""
            SELECT title, content, difficulty_score, private, shareable 
            FROM reading_sessions WHERE id = ?
        """, (session_id,))
        title, content, difficulty, private, shareable = cursor.fetchone()
        assert title == 'Updated Title'
        assert content == 'Updated Content'
        assert difficulty == 0.75
        assert private == 1
        assert shareable == 0
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_after_delete_and_reinsert(self, db):
        """
        Test that privacy invariant holds after delete and reinsert operations.
        
        Operation: INSERT, DELETE, INSERT
        Expected: Privacy invariant holds throughout
        """
        cursor = db.conn.cursor()
        
        # Insert a session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Article 1', 'Content 1', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        session_id = cursor.lastrowid
        db.conn.commit()
        
        # Verify privacy invariant
        self._verify_privacy_invariant(db)
        
        # Delete the session
        cursor.execute("DELETE FROM reading_sessions WHERE id = ?", (session_id,))
        db.conn.commit()
        
        # Verify privacy invariant (vacuously true for empty table)
        self._verify_privacy_invariant(db)
        
        # Insert a new session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Article 2', 'Content 2', 'ko', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        db.conn.commit()
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    @pytest.mark.parametrize("user_id,title,content,language", [
        (1, "Article A", "Content A", "en"),
        (2, "Article B", "Content B", "ko"),
        (3, "Article C", "Content C", "ja"),
        (1, "Article D", "Content D", "es"),
        (2, "Article E", "Content E", "fr"),
    ])
    def test_privacy_invariant_across_users(self, db, user_id, title, content, language):
        """
        Test that privacy invariant holds for sessions from different users.
        
        Operation: INSERT sessions for multiple users
        Expected: All sessions are private and non-shareable
        """
        cursor = db.conn.cursor()
        
        # Insert session for specific user
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (?, ?, ?, ?, 'user_paste', 'paste', 1, 1, 0)
        """, (user_id, title, content, language))
        db.conn.commit()
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_with_default_values(self, db):
        """
        Test that privacy invariant holds when using default column values.
        
        Operation: INSERT without explicitly setting private/shareable
        Expected: Defaults are applied and invariant holds
        """
        cursor = db.conn.cursor()
        
        # Insert session relying on default values for private and shareable
        # Note: legal_attestation has CHECK constraint so must be explicit
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, legal_attestation)
            VALUES (1, 'Test Article', 'Content', 'en', 'user_paste', 'paste', 1)
        """)
        db.conn.commit()
        
        # Verify the session was created with correct defaults
        cursor.execute("""
            SELECT private, shareable FROM reading_sessions
        """)
        private, shareable = cursor.fetchone()
        assert private == 1, "Default value for private should be 1"
        assert shareable == 0, "Default value for shareable should be 0"
        
        # Verify privacy invariant holds
        self._verify_privacy_invariant(db)

    def test_privacy_invariant_comprehensive_stress_test(self, db):
        """
        Comprehensive stress test: multiple operations, verify invariant throughout.
        
        Operations: Multiple INSERTs, UPDATEs, DELETEs
        Expected: Privacy invariant holds after every operation
        """
        cursor = db.conn.cursor()
        
        # Insert 10 sessions
        for i in range(10):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (?, ?, ?, 'en', 'user_paste', 'paste', 1, 1, 0)
            """, (i % 3 + 1, f'Article {i}', f'Content {i}'))
        db.conn.commit()
        
        # Verify invariant after inserts
        self._verify_privacy_invariant(db)
        
        # Update some sessions (valid updates)
        cursor.execute("""
            UPDATE reading_sessions 
            SET difficulty_score = 0.5 
            WHERE id <= 5
        """)
        db.conn.commit()
        
        # Verify invariant after updates
        self._verify_privacy_invariant(db)
        
        # Delete some sessions
        cursor.execute("DELETE FROM reading_sessions WHERE id > 7")
        db.conn.commit()
        
        # Verify invariant after deletes
        self._verify_privacy_invariant(db)
        
        # Insert more sessions
        for i in range(10, 15):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (?, ?, ?, 'ko', 'user_file', 'file', 1, 1, 0)
            """, (i % 2 + 1, f'Article {i}', f'Content {i}'))
        db.conn.commit()
        
        # Final verification
        self._verify_privacy_invariant(db)
        
        # Verify we have the expected number of sessions
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        count = cursor.fetchone()[0]
        assert count == 12  # 7 from first batch + 5 from second batch
