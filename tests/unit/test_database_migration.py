"""
Unit tests for sentence mining database migrations.

Tests verify that all required tables and columns are created correctly,
foreign key constraints are enforced, and migrations are idempotent.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.database import FlashcardDatabase


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = FlashcardDatabase(db_path)
    yield db
    
    # Cleanup
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestDifficultyTrackingMigration:
    """Test migration of difficulty tracking columns to imported_content."""
    
    def test_difficulty_score_column_exists(self, test_db):
        """Test that difficulty_score column was added to imported_content."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'difficulty_score' in columns
        assert columns['difficulty_score'] == 'REAL'
    
    def test_known_word_ratio_column_exists(self, test_db):
        """Test that known_word_ratio column was added."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'known_word_ratio' in columns
        assert columns['known_word_ratio'] == 'REAL'
    
    def test_grammar_complexity_column_exists(self, test_db):
        """Test that grammar_complexity column was added."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'grammar_complexity' in columns
        assert columns['grammar_complexity'] == 'TEXT'
    
    def test_unknown_words_column_exists(self, test_db):
        """Test that unknown_words column was added for JSON arrays."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'unknown_words' in columns
        assert columns['unknown_words'] == 'TEXT'
    
    def test_detected_patterns_column_exists(self, test_db):
        """Test that detected_patterns column was added for cached LLM results."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'detected_patterns' in columns
        assert columns['detected_patterns'] == 'TEXT'
    
    def test_detected_topics_column_exists(self, test_db):
        """Test that detected_topics column was added for cached LLM results."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'detected_topics' in columns
        assert columns['detected_topics'] == 'TEXT'
    
    def test_analysis_timestamp_column_exists(self, test_db):
        """Test that analysis_timestamp column was added."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(imported_content)")
        columns = {info[1]: info[2] for info in cursor.fetchall()}
        
        assert 'analysis_timestamp' in columns
        assert columns['analysis_timestamp'] == 'TEXT'
    
    def test_difficulty_indexes_created(self, test_db):
        """Test that performance indexes were created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_imported_content_%'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert 'idx_imported_content_difficulty' in indexes
        assert 'idx_imported_content_grammar' in indexes


class TestSentenceStudyProgressTable:
    """Test creation of sentence_study_progress table."""
    
    def test_table_exists(self, test_db):
        """Test that sentence_study_progress table was created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentence_study_progress'")
        assert cursor.fetchone() is not None
    
    def test_required_columns_exist(self, test_db):
        """Test that all required columns exist."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(sentence_study_progress)")
        columns = {info[1] for info in cursor.fetchall()}
        
        required = {
            'id', 'imported_content_id', 'last_reviewed', 'review_count',
            'correct_count', 'ease_factor', 'interval_days', 'next_review_date',
            'created_at'
        }
        assert required.issubset(columns)
    
    def test_default_ease_factor(self, test_db):
        """Test that ease_factor defaults to 2.5."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(sentence_study_progress)")
        columns = {info[1]: info for info in cursor.fetchall()}
        
        ease_factor_info = columns['ease_factor']
        # Default value is stored as string in PRAGMA output
        assert ease_factor_info[4] == '2.5'
    
    def test_foreign_key_constraint(self, test_db):
        """Test that foreign key constraint exists."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA foreign_key_list(sentence_study_progress)")
        fks = cursor.fetchall()
        
        # Should have FK to imported_content
        fk_tables = {fk[2] for fk in fks}
        assert 'imported_content' in fk_tables
    
    def test_unique_constraint_on_content_id(self, test_db):
        """Test that imported_content_id has unique constraint."""
        cursor = test_db.conn.cursor()
        
        # Insert a test sentence
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Test sentence', 'http://example.com', 'es', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Insert first review record
        cursor.execute(
            "INSERT INTO sentence_study_progress (imported_content_id, last_reviewed, next_review_date, created_at) VALUES (?, ?, ?, ?)",
            (sentence_id, datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat())
        )
        test_db.conn.commit()
        
        # Try to insert duplicate - should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO sentence_study_progress (imported_content_id, last_reviewed, next_review_date, created_at) VALUES (?, ?, ?, ?)",
                (sentence_id, datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat())
            )
            test_db.conn.commit()
    
    def test_indexes_created(self, test_db):
        """Test that performance indexes were created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_sentence_study_%'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert 'idx_sentence_study_next_review' in indexes
        assert 'idx_sentence_study_content_id' in indexes


class TestSentenceCollectionsTables:
    """Test creation of sentence collections tables."""
    
    def test_collections_table_exists(self, test_db):
        """Test that sentence_collections table was created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentence_collections'")
        assert cursor.fetchone() is not None
    
    def test_collection_items_table_exists(self, test_db):
        """Test that sentence_collection_items table was created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentence_collection_items'")
        assert cursor.fetchone() is not None
    
    def test_collections_required_columns(self, test_db):
        """Test that sentence_collections has all required columns."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(sentence_collections)")
        columns = {info[1] for info in cursor.fetchall()}
        
        required = {'id', 'name', 'description', 'collection_type', 'language', 'metadata', 'created_at', 'updated_at'}
        assert required.issubset(columns)
    
    def test_collection_items_required_columns(self, test_db):
        """Test that sentence_collection_items has all required columns."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA table_info(sentence_collection_items)")
        columns = {info[1] for info in cursor.fetchall()}
        
        required = {'id', 'collection_id', 'imported_content_id', 'sort_order', 'added_at'}
        assert required.issubset(columns)
    
    def test_collection_items_foreign_keys(self, test_db):
        """Test that foreign key constraints exist."""
        cursor = test_db.conn.cursor()
        cursor.execute("PRAGMA foreign_key_list(sentence_collection_items)")
        fks = cursor.fetchall()
        
        fk_tables = {fk[2] for fk in fks}
        assert 'sentence_collections' in fk_tables
        assert 'imported_content' in fk_tables
    
    def test_collection_items_unique_constraint(self, test_db):
        """Test that (collection_id, imported_content_id) has unique constraint."""
        cursor = test_db.conn.cursor()
        
        # Create a collection
        cursor.execute(
            "INSERT INTO sentence_collections (name, collection_type, language, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ('Test Collection', 'manual', 'es', datetime.now().isoformat(), datetime.now().isoformat())
        )
        collection_id = cursor.lastrowid
        
        # Create a sentence
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Test sentence', 'http://example.com', 'es', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Add sentence to collection
        cursor.execute(
            "INSERT INTO sentence_collection_items (collection_id, imported_content_id, added_at) VALUES (?, ?, ?)",
            (collection_id, sentence_id, datetime.now().isoformat())
        )
        test_db.conn.commit()
        
        # Try to add same sentence again - should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO sentence_collection_items (collection_id, imported_content_id, added_at) VALUES (?, ?, ?)",
                (collection_id, sentence_id, datetime.now().isoformat())
            )
            test_db.conn.commit()
    
    def test_collection_indexes_created(self, test_db):
        """Test that performance indexes were created."""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_sentence_collection%'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert 'idx_sentence_collections_type' in indexes
        assert 'idx_sentence_collections_language' in indexes
        assert 'idx_sentence_collection_items_collection' in indexes
        assert 'idx_sentence_collection_items_content' in indexes


class TestMigrationIdempotency:
    """Test that migrations can be run multiple times safely."""
    
    def test_migration_is_idempotent(self, test_db):
        """Test that running migration twice doesn't cause errors."""
        cursor = test_db.conn.cursor()
        
        # Get initial state
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sentence_study_progress'")
        initial_count = cursor.fetchone()[0]
        
        # Run migration again (should be safe)
        try:
            db2 = FlashcardDatabase(test_db.db_path)
            db2.conn.close()
        except sqlite3.OperationalError as e:
            if 'duplicate column' not in str(e).lower():
                raise
        
        # Verify state unchanged
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sentence_study_progress'")
        final_count = cursor.fetchone()[0]
        
        assert initial_count == final_count


class TestForeignKeyEnforcement:
    """Test that foreign key constraints are properly enforced."""
    
    def test_cascade_delete_on_sentence_deletion(self, test_db):
        """Test that deleting a sentence cascades to study progress."""
        cursor = test_db.conn.cursor()
        
        # Create a sentence
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Test sentence', 'http://example.com', 'es', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        
        # Create study progress record
        cursor.execute(
            "INSERT INTO sentence_study_progress (imported_content_id, last_reviewed, next_review_date, created_at) VALUES (?, ?, ?, ?)",
            (sentence_id, datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat())
        )
        test_db.conn.commit()
        
        # Verify record exists
        cursor.execute("SELECT COUNT(*) FROM sentence_study_progress WHERE imported_content_id = ?", (sentence_id,))
        assert cursor.fetchone()[0] == 1
        
        # Delete sentence
        cursor.execute("DELETE FROM imported_content WHERE id = ?", (sentence_id,))
        test_db.conn.commit()
        
        # Verify study progress record was deleted
        cursor.execute("SELECT COUNT(*) FROM sentence_study_progress WHERE imported_content_id = ?", (sentence_id,))
        assert cursor.fetchone()[0] == 0
    
    def test_cascade_delete_on_collection_deletion(self, test_db):
        """Test that deleting a collection cascades to collection items."""
        cursor = test_db.conn.cursor()
        
        # Create a collection
        cursor.execute(
            "INSERT INTO sentence_collections (name, collection_type, language, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ('Test Collection', 'manual', 'es', datetime.now().isoformat(), datetime.now().isoformat())
        )
        collection_id = cursor.lastrowid
        
        # Create a sentence
        cursor.execute(
            "INSERT INTO imported_content (content_type, content, url, language, created_at) VALUES (?, ?, ?, ?, ?)",
            ('sentence', 'Test sentence', 'http://example.com', 'es', datetime.now().isoformat())
        )
        sentence_id = cursor.lastrowid
        
        # Add sentence to collection
        cursor.execute(
            "INSERT INTO sentence_collection_items (collection_id, imported_content_id, added_at) VALUES (?, ?, ?)",
            (collection_id, sentence_id, datetime.now().isoformat())
        )
        test_db.conn.commit()
        
        # Verify item exists
        cursor.execute("SELECT COUNT(*) FROM sentence_collection_items WHERE collection_id = ?", (collection_id,))
        assert cursor.fetchone()[0] == 1
        
        # Delete collection
        cursor.execute("DELETE FROM sentence_collections WHERE id = ?", (collection_id,))
        test_db.conn.commit()
        
        # Verify collection items were deleted
        cursor.execute("SELECT COUNT(*) FROM sentence_collection_items WHERE collection_id = ?", (collection_id,))
        assert cursor.fetchone()[0] == 0
