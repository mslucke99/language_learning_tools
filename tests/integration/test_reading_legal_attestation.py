"""
Property-based tests for Immersive Reading Mode legal attestation requirement.

These tests verify that the legal attestation requirement is enforced
for all content import operations.

Property 2: Legal Attestation Required
- Validates: Requirements 1.3, 22.9
- Verifies import attempts with attestation=False raise errors
"""

import sqlite3
import tempfile
import os
import pytest
from src.core.database import FlashcardDatabase


class TestLegalAttestationRequired:
    """
    Property 2: Legal Attestation Required
    
    This property ensures that ALL reading sessions require explicit legal attestation
    from the user confirming they have legal rights to the imported content.
    This is a critical legal compliance requirement to protect both users and developers
    from copyright infringement.
    
    The property verifies:
    1. Sessions cannot be created with legal_attestation=False
    2. Sessions cannot be created without legal_attestation field
    3. All existing sessions have legal_attestation=True
    4. Attestation cannot be removed after creation
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

    def _verify_attestation_invariant(self, db: FlashcardDatabase) -> None:
        """
        Helper method to verify the legal attestation invariant holds.
        
        Checks that ALL reading_sessions have:
        - legal_attestation = 1 (TRUE)
        
        Raises AssertionError if any session violates the invariant.
        """
        cursor = db.conn.cursor()
        
        # Check for any sessions without legal attestation
        cursor.execute("""
            SELECT id, title, legal_attestation 
            FROM reading_sessions 
            WHERE legal_attestation != 1 OR legal_attestation IS NULL
        """)
        violations = cursor.fetchall()
        
        assert len(violations) == 0, (
            f"Legal attestation invariant violated! Found {len(violations)} session(s) "
            f"without legal attestation: {violations}"
        )
        
        # Also verify all sessions have attestation
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM reading_sessions 
            WHERE legal_attestation = 1
        """)
        attested_sessions = cursor.fetchone()[0]
        
        assert total_sessions == attested_sessions, (
            f"Legal attestation invariant violated! {total_sessions} total sessions but only "
            f"{attested_sessions} have legal attestation"
        )

    def test_attestation_required_prevents_false_insert(self, db):
        """
        Test that sessions cannot be created with legal_attestation=False.
        
        Operation: INSERT with legal_attestation=0
        Expected: Insert fails with IntegrityError
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert session without attestation (should fail)
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Unattested Article', 'Content', 'en', 
                        'user_paste', 'paste', 0, 1, 0)
            """)
        
        # Verify the error message mentions the constraint
        error_msg = str(exc_info.value).lower()
        assert "legal" in error_msg and "attestation" in error_msg
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify attestation invariant holds (vacuously true for empty table)
        self._verify_attestation_invariant(db)

    def test_attestation_required_prevents_null_insert(self, db):
        """
        Test that sessions cannot be created with legal_attestation=NULL.
        
        Operation: INSERT with legal_attestation=NULL
        Expected: Insert fails with IntegrityError
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert session with NULL attestation (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Null Attestation Article', 'Content', 'en', 
                        'user_paste', 'paste', NULL, 1, 0)
            """)
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_allows_true_insert(self, db):
        """
        Test that sessions CAN be created with legal_attestation=True.
        
        Operation: INSERT with legal_attestation=1
        Expected: Insert succeeds
        """
        cursor = db.conn.cursor()
        
        # Insert session with valid attestation (should succeed)
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Attested Article', 'Content', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        db.conn.commit()
        
        # Verify session was created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 1
        
        # Verify attestation value
        cursor.execute("SELECT legal_attestation FROM reading_sessions")
        attestation = cursor.fetchone()[0]
        assert attestation == 1
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_prevents_update_to_false(self, db):
        """
        Test that legal_attestation cannot be changed to False after creation.
        
        Operation: UPDATE to set legal_attestation=0
        Expected: Update fails, attestation remains True
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
        
        # Attempt to update attestation to false (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE reading_sessions 
                SET legal_attestation = 0 
                WHERE id = ?
            """, (session_id,))
        
        # Verify attestation is still true
        cursor.execute("""
            SELECT legal_attestation FROM reading_sessions WHERE id = ?
        """, (session_id,))
        attestation = cursor.fetchone()[0]
        assert attestation == 1
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_prevents_update_to_null(self, db):
        """
        Test that legal_attestation cannot be changed to NULL after creation.
        
        Operation: UPDATE to set legal_attestation=NULL
        Expected: Update fails, attestation remains True
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
        
        # Attempt to update attestation to NULL (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE reading_sessions 
                SET legal_attestation = NULL 
                WHERE id = ?
            """, (session_id,))
        
        # Verify attestation is still true
        cursor.execute("""
            SELECT legal_attestation FROM reading_sessions WHERE id = ?
        """, (session_id,))
        attestation = cursor.fetchone()[0]
        assert attestation == 1
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_after_multiple_inserts(self, db):
        """
        Test that attestation invariant holds after multiple valid inserts.
        
        Operation: Multiple INSERT operations with attestation=True
        Expected: All sessions created with legal_attestation=True
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
        
        # Verify attestation invariant holds for all sessions
        self._verify_attestation_invariant(db)

    def test_attestation_required_mixed_insert_attempts(self, db):
        """
        Test that only attested sessions are created when mixing valid and invalid inserts.
        
        Operation: Attempt multiple INSERTs, some with attestation=True, some with False
        Expected: Only attested sessions are created, others fail
        """
        cursor = db.conn.cursor()
        
        # Insert valid session (should succeed)
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Valid Article 1', 'Content', 'en', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        db.conn.commit()
        
        # Attempt invalid insert (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Invalid Article', 'Content', 'en', 
                        'user_paste', 'paste', 0, 1, 0)
            """)
        
        # Insert another valid session (should succeed)
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Valid Article 2', 'Content', 'ko', 
                    'user_paste', 'paste', 1, 1, 0)
        """)
        db.conn.commit()
        
        # Verify only valid sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 2
        
        # Verify all created sessions have attestation
        self._verify_attestation_invariant(db)

    def test_attestation_required_allows_valid_updates(self, db):
        """
        Test that attestation invariant allows updates to other fields.
        
        Operation: UPDATE to modify title, content, etc. (not attestation)
        Expected: Update succeeds, attestation unchanged
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
            SELECT title, content, difficulty_score, legal_attestation 
            FROM reading_sessions WHERE id = ?
        """, (session_id,))
        title, content, difficulty, attestation = cursor.fetchone()
        assert title == 'Updated Title'
        assert content == 'Updated Content'
        assert difficulty == 0.75
        assert attestation == 1
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    @pytest.mark.parametrize("attestation_value", [0, -1, 2, 99, None])
    def test_attestation_required_rejects_invalid_values(self, db, attestation_value):
        """
        Test that only legal_attestation=1 is accepted.
        
        Operation: INSERT with various invalid attestation values
        Expected: All inserts fail except attestation=1
        """
        cursor = db.conn.cursor()
        
        # Attempt to insert with invalid attestation value (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Test Article', 'Content', 'en', 
                        'user_paste', 'paste', ?, 1, 0)
            """, (attestation_value,))
        
        # Verify no sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == 0
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_comprehensive_stress_test(self, db):
        """
        Comprehensive stress test: multiple operations, verify invariant throughout.
        
        Operations: Multiple valid INSERTs, invalid INSERT attempts, UPDATEs, DELETEs
        Expected: Attestation invariant holds after every operation
        """
        cursor = db.conn.cursor()
        
        # Insert 10 valid sessions
        for i in range(10):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (?, ?, ?, 'en', 'user_paste', 'paste', 1, 1, 0)
            """, (i % 3 + 1, f'Article {i}', f'Content {i}'))
        db.conn.commit()
        
        # Verify invariant after inserts
        self._verify_attestation_invariant(db)
        
        # Attempt to insert invalid sessions (should all fail)
        for i in range(10, 15):
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO reading_sessions 
                    (user_id, title, content, language, source, import_method, 
                     legal_attestation, private, shareable)
                    VALUES (?, ?, ?, 'en', 'user_paste', 'paste', 0, 1, 0)
                """, (i % 3 + 1, f'Invalid Article {i}', f'Content {i}'))
        
        # Verify invariant after failed inserts
        self._verify_attestation_invariant(db)
        
        # Update some sessions (valid updates)
        cursor.execute("""
            UPDATE reading_sessions 
            SET difficulty_score = 0.5 
            WHERE id <= 5
        """)
        db.conn.commit()
        
        # Verify invariant after updates
        self._verify_attestation_invariant(db)
        
        # Attempt to update attestation to false (should fail)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE reading_sessions 
                SET legal_attestation = 0 
                WHERE id = 1
            """)
        
        # Verify invariant after failed update
        self._verify_attestation_invariant(db)
        
        # Delete some sessions
        cursor.execute("DELETE FROM reading_sessions WHERE id > 7")
        db.conn.commit()
        
        # Verify invariant after deletes
        self._verify_attestation_invariant(db)
        
        # Insert more valid sessions
        for i in range(15, 20):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (?, ?, ?, 'ko', 'user_file', 'file', 1, 1, 0)
            """, (i % 2 + 1, f'Article {i}', f'Content {i}'))
        db.conn.commit()
        
        # Final verification
        self._verify_attestation_invariant(db)
        
        # Verify we have the expected number of sessions
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        count = cursor.fetchone()[0]
        assert count == 12  # 7 from first batch + 5 from second batch

    def test_attestation_required_with_audit_trail(self, db):
        """
        Test that attestation is properly recorded alongside audit trail information.
        
        Operation: INSERT with attestation and audit trail fields
        Expected: All fields stored correctly, attestation=True
        """
        cursor = db.conn.cursor()
        
        # Insert session with full audit trail
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, import_ip_address, import_user_agent,
             private, shareable)
            VALUES (1, 'Audited Article', 'Content', 'en', 
                    'user_paste', 'paste', 1, '192.168.1.1', 
                    'Mozilla/5.0', 1, 0)
        """)
        db.conn.commit()
        
        # Verify all fields were stored
        cursor.execute("""
            SELECT legal_attestation, import_ip_address, import_user_agent 
            FROM reading_sessions
        """)
        attestation, ip, user_agent = cursor.fetchone()
        assert attestation == 1
        assert ip == '192.168.1.1'
        assert user_agent == 'Mozilla/5.0'
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)

    def test_attestation_required_across_import_methods(self, db):
        """
        Test that attestation is required regardless of import method.
        
        Operation: INSERT sessions with different import methods
        Expected: All require attestation=True
        """
        cursor = db.conn.cursor()
        
        import_methods = [
            ('user_paste', 'paste'),
            ('user_file', 'file'),
        ]
        
        for source, method in import_methods:
            # Valid insert with attestation (should succeed)
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, ?, 'Content', 'en', ?, ?, 1, 1, 0)
            """, (f'Article from {method}', source, method))
            db.conn.commit()
            
            # Invalid insert without attestation (should fail)
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO reading_sessions 
                    (user_id, title, content, language, source, import_method, 
                     legal_attestation, private, shareable)
                    VALUES (1, ?, 'Content', 'en', ?, ?, 0, 1, 0)
                """, (f'Invalid Article from {method}', source, method))
        
        # Verify only valid sessions were created
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        assert cursor.fetchone()[0] == len(import_methods)
        
        # Verify attestation invariant holds
        self._verify_attestation_invariant(db)
