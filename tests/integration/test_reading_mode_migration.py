"""
Integration test for reading mode database schema migration.

Tests that the database migration creates all required tables, indexes,
and triggers for the Immersive Reading Mode feature.
"""

import sqlite3
import tempfile
import os
import pytest
from src.core.database import FlashcardDatabase


class TestReadingModeMigration:
    """Test database migration for reading mode tables."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_migration_creates_all_tables(self, temp_db):
        """Test that migration creates all 7 reading mode tables."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        # Check that all 7 tables exist
        expected_tables = [
            'reading_sessions',
            'reading_progress',
            'reading_lookups',
            'reading_definition_cache',
            'reading_annotations',
            'reading_comprehension',
            'reading_terms_acceptance'
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in expected_tables:
            assert table in tables, f"Table {table} was not created"

        db.close()

    def test_reading_sessions_schema(self, temp_db):
        """Test reading_sessions table has all required columns."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        cursor.execute("PRAGMA table_info(reading_sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # Check required columns exist
        required_columns = [
            'id', 'user_id', 'title', 'content', 'language',
            'source', 'import_method', 'content_type',
            'difficulty_score', 'difficulty_rating', 'word_count',
            'estimated_minutes', 'legal_attestation', 'import_ip_address',
            'import_user_agent', 'private', 'shareable',
            'created_at', 'last_read_at'
        ]

        for col in required_columns:
            assert col in columns, f"Column {col} missing from reading_sessions"

        db.close()

    def test_indexes_created(self, temp_db):
        """Test that all required indexes are created."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        expected_indexes = [
            'idx_reading_sessions_user',
            'idx_reading_sessions_language',
            'idx_reading_progress_session',
            'idx_reading_lookups_session',
            'idx_reading_lookups_word',
            'idx_definition_cache_lookup',
            'idx_reading_annotations_session',
            'idx_reading_comprehension_session',
            'idx_terms_acceptance_user'
        ]

        for idx in expected_indexes:
            assert idx in indexes, f"Index {idx} was not created"

        db.close()

    def test_triggers_created(self, temp_db):
        """Test that legal compliance triggers are created."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        triggers = [row[0] for row in cursor.fetchall()]

        expected_triggers = [
            'enforce_privacy_on_insert',
            'enforce_privacy_on_update',
            'enforce_attestation_on_insert'
        ]

        for trigger in expected_triggers:
            assert trigger in triggers, f"Trigger {trigger} was not created"

        db.close()

    def test_privacy_trigger_enforcement(self, temp_db):
        """Test that privacy triggers prevent public/shareable sessions."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        # Try to insert a public session (should fail)
        with pytest.raises(sqlite3.IntegrityError, match="private and non-shareable"):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Test', 'Content', 'en', 'user_paste', 'paste', 1, 0, 0)
            """)

        # Try to insert a shareable session (should fail)
        with pytest.raises(sqlite3.IntegrityError, match="private and non-shareable"):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Test', 'Content', 'en', 'user_paste', 'paste', 1, 1, 1)
            """)

        db.close()

    def test_attestation_trigger_enforcement(self, temp_db):
        """Test that attestation trigger requires legal_attestation=1."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        # Try to insert without attestation (should fail)
        with pytest.raises(sqlite3.IntegrityError, match="Legal attestation is required"):
            cursor.execute("""
                INSERT INTO reading_sessions 
                (user_id, title, content, language, source, import_method, 
                 legal_attestation, private, shareable)
                VALUES (1, 'Test', 'Content', 'en', 'user_paste', 'paste', 0, 1, 0)
            """)

        db.close()

    def test_valid_session_insertion(self, temp_db):
        """Test that valid sessions can be inserted successfully."""
        db = FlashcardDatabase(db_name=temp_db)
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

        # Verify it was inserted
        cursor.execute("SELECT COUNT(*) FROM reading_sessions")
        count = cursor.fetchone()[0]
        assert count == 1, "Valid session was not inserted"

        db.close()

    def test_cascade_delete(self, temp_db):
        """Test that deleting a session cascades to related tables."""
        db = FlashcardDatabase(db_name=temp_db)
        cursor = db.conn.cursor()

        # Insert a session
        cursor.execute("""
            INSERT INTO reading_sessions 
            (user_id, title, content, language, source, import_method, 
             legal_attestation, private, shareable)
            VALUES (1, 'Test', 'Content', 'en', 'user_paste', 'paste', 1, 1, 0)
        """)
        session_id = cursor.lastrowid

        # Insert related records
        cursor.execute("""
            INSERT INTO reading_progress (session_id, user_id)
            VALUES (?, 1)
        """, (session_id,))

        cursor.execute("""
            INSERT INTO reading_lookups 
            (session_id, user_id, lookup_type, sentence_context)
            VALUES (?, 1, 'word', 'Test sentence')
        """, (session_id,))

        cursor.execute("""
            INSERT INTO reading_annotations 
            (session_id, user_id, start_position, end_position, annotation_type)
            VALUES (?, 1, 0, 10, 'highlight')
        """, (session_id,))

        db.conn.commit()

        # Delete the session
        cursor.execute("DELETE FROM reading_sessions WHERE id = ?", (session_id,))
        db.conn.commit()

        # Verify cascade delete worked
        cursor.execute("SELECT COUNT(*) FROM reading_progress WHERE session_id = ?", (session_id,))
        assert cursor.fetchone()[0] == 0, "reading_progress not cascade deleted"

        cursor.execute("SELECT COUNT(*) FROM reading_lookups WHERE session_id = ?", (session_id,))
        assert cursor.fetchone()[0] == 0, "reading_lookups not cascade deleted"

        cursor.execute("SELECT COUNT(*) FROM reading_annotations WHERE session_id = ?", (session_id,))
        assert cursor.fetchone()[0] == 0, "reading_annotations not cascade deleted"

        db.close()

    def test_migration_idempotency(self, temp_db):
        """Test that migration can be run multiple times safely."""
        db = FlashcardDatabase(db_name=temp_db)
        
        # Run migration again (it's called in __init__)
        db._migrate_schema()
        
        # Verify tables still exist and no errors occurred
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_sessions'")
        result = cursor.fetchone()
        assert result is not None, "Migration is not idempotent"

        db.close()
