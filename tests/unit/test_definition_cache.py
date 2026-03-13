"""Unit tests for DefinitionCache class."""

import pytest
import tempfile
import os
from datetime import datetime
from src.core.database import FlashcardDatabase
from src.features.reader.definition_cache import DefinitionCache


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = FlashcardDatabase(path)
    yield db
    db.conn.close()
    os.unlink(path)


@pytest.fixture
def cache(temp_db):
    """Create a DefinitionCache instance."""
    return DefinitionCache(temp_db)


class TestDefinitionCacheInit:
    """Test DefinitionCache initialization."""
    
    def test_init_with_database(self, temp_db):
        """Test that DefinitionCache initializes with a database."""
        cache = DefinitionCache(temp_db)
        assert cache.db is not None
        assert cache.db == temp_db


class TestGetDefinition:
    """Test get_definition method."""
    
    def test_get_definition_not_found(self, cache):
        """Test getting a definition that doesn't exist returns None."""
        result = cache.get_definition("hello", "en", "Hello world")
        assert result is None
    
    def test_get_definition_found_with_context(self, cache, temp_db):
        """Test getting a cached definition with matching context."""
        # Store a definition
        cache.store_definition(
            word="hello",
            language="en",
            context="Hello world",
            definition="A greeting",
            synonym="hi",
            example="Hello, how are you?"
        )
        
        # Retrieve it
        result = cache.get_definition("hello", "en", "Hello world")
        assert result is not None
        assert result['word'] == "hello"
        assert result['definition'] == "A greeting"
        assert result['synonym'] == "hi"
        assert result['example'] == "Hello, how are you?"
        assert result['source'] == 'cache'
    
    def test_get_definition_fallback_to_generic(self, cache):
        """Test fallback to generic cache when context-specific not found."""
        # Store a generic definition (empty context)
        cache.store_definition(
            word="hello",
            language="en",
            context="",
            definition="A generic greeting",
            synonym=None,
            example="Hello!"
        )
        
        # Try to get with different context - should fall back to generic
        result = cache.get_definition("hello", "en", "Hello world")
        assert result is not None
        assert result['definition'] == "A generic greeting"
        assert result['source'] == 'cache'


class TestStoreDefinition:
    """Test store_definition method."""
    
    def test_store_definition_basic(self, cache, temp_db):
        """Test storing a basic definition."""
        cache.store_definition(
            word="test",
            language="en",
            context="This is a test",
            definition="A procedure to check something",
            synonym="examination",
            example="We need to test this code"
        )
        
        # Verify it was stored
        cursor = temp_db.conn.cursor()
        cursor.execute(
            "SELECT word, language, definition, synonym, example_sentence FROM reading_definition_cache WHERE word = ?",
            ("test",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test"
        assert row[1] == "en"
        assert row[2] == "A procedure to check something"
        assert row[3] == "examination"
        assert row[4] == "We need to test this code"
    
    def test_store_definition_without_optional_fields(self, cache, temp_db):
        """Test storing a definition without synonym and example."""
        cache.store_definition(
            word="word",
            language="en",
            context="A word",
            definition="A unit of language",
            synonym=None,
            example=None
        )
        
        # Verify it was stored
        cursor = temp_db.conn.cursor()
        cursor.execute(
            "SELECT word, definition, synonym, example_sentence FROM reading_definition_cache WHERE word = ?",
            ("word",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "word"
        assert row[1] == "A unit of language"
        assert row[2] is None
        assert row[3] is None
    
    def test_store_definition_duplicate_updates(self, cache, temp_db):
        """Test that storing a duplicate definition updates the existing one."""
        # Store initial definition
        cache.store_definition(
            word="update",
            language="en",
            context="Update the system",
            definition="Old definition",
            synonym=None,
            example=None
        )
        
        # Store again with same word, language, context
        cache.store_definition(
            word="update",
            language="en",
            context="Update the system",
            definition="New definition",
            synonym="refresh",
            example="Update your software"
        )
        
        # Verify only one record exists with new data
        cursor = temp_db.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*), definition, synonym FROM reading_definition_cache WHERE word = ?",
            ("update",)
        )
        row = cursor.fetchone()
        assert row[0] == 1  # Only one record
        assert row[1] == "New definition"
        assert row[2] == "refresh"


class TestHashContext:
    """Test _hash_context method."""
    
    def test_hash_context_consistent(self, cache):
        """Test that hashing the same context produces the same hash."""
        context = "This is a test context"
        hash1 = cache._hash_context(context)
        hash2 = cache._hash_context(context)
        assert hash1 == hash2
    
    def test_hash_context_different(self, cache):
        """Test that different contexts produce different hashes."""
        hash1 = cache._hash_context("Context A")
        hash2 = cache._hash_context("Context B")
        assert hash1 != hash2
    
    def test_hash_context_empty(self, cache):
        """Test hashing an empty context."""
        hash_empty = cache._hash_context("")
        assert hash_empty is not None
        assert len(hash_empty) == 32  # MD5 produces 32 character hex string


class TestUpdateAccess:
    """Test _update_access method."""
    
    def test_update_access_increments_count(self, cache, temp_db):
        """Test that accessing a definition increments access_count."""
        # Store a definition
        cache.store_definition(
            word="access",
            language="en",
            context="Access the file",
            definition="To get or use something",
            synonym=None,
            example=None
        )
        
        # Get initial access count
        cursor = temp_db.conn.cursor()
        context_hash = cache._hash_context("Access the file")
        cursor.execute(
            "SELECT access_count FROM reading_definition_cache WHERE word = ? AND language = ? AND context_hash = ?",
            ("access", "en", context_hash)
        )
        initial_count = cursor.fetchone()[0]
        
        # Update access
        cache._update_access("access", "en", context_hash)
        
        # Verify count incremented
        cursor.execute(
            "SELECT access_count FROM reading_definition_cache WHERE word = ? AND language = ? AND context_hash = ?",
            ("access", "en", context_hash)
        )
        new_count = cursor.fetchone()[0]
        assert new_count == initial_count + 1
    
    def test_update_access_updates_timestamp(self, cache, temp_db):
        """Test that accessing a definition updates last_accessed timestamp."""
        # Store a definition
        cache.store_definition(
            word="timestamp",
            language="en",
            context="Check the timestamp",
            definition="A record of time",
            synonym=None,
            example=None
        )
        
        # Get initial timestamp
        cursor = temp_db.conn.cursor()
        context_hash = cache._hash_context("Check the timestamp")
        cursor.execute(
            "SELECT last_accessed FROM reading_definition_cache WHERE word = ? AND language = ? AND context_hash = ?",
            ("timestamp", "en", context_hash)
        )
        initial_time = cursor.fetchone()[0]
        
        # Wait a tiny bit and update access
        import time
        time.sleep(0.01)
        cache._update_access("timestamp", "en", context_hash)
        
        # Verify timestamp updated
        cursor.execute(
            "SELECT last_accessed FROM reading_definition_cache WHERE word = ? AND language = ? AND context_hash = ?",
            ("timestamp", "en", context_hash)
        )
        new_time = cursor.fetchone()[0]
        assert new_time > initial_time


class TestIntegration:
    """Integration tests for DefinitionCache."""
    
    def test_store_and_retrieve_workflow(self, cache):
        """Test complete workflow of storing and retrieving definitions."""
        # Store multiple definitions
        cache.store_definition(
            word="run",
            language="en",
            context="I run every morning",
            definition="To move quickly on foot",
            synonym="jog",
            example="She runs 5 miles daily"
        )
        
        cache.store_definition(
            word="run",
            language="en",
            context="Run the program",
            definition="To execute software",
            synonym="execute",
            example="Run the script"
        )
        
        # Retrieve context-specific definition
        result1 = cache.get_definition("run", "en", "I run every morning")
        assert result1['definition'] == "To move quickly on foot"
        
        result2 = cache.get_definition("run", "en", "Run the program")
        assert result2['definition'] == "To execute software"
    
    def test_access_tracking_on_get(self, cache, temp_db):
        """Test that get_definition updates access tracking."""
        # Store a definition
        cache.store_definition(
            word="track",
            language="en",
            context="Track the package",
            definition="To follow or monitor",
            synonym=None,
            example=None
        )
        
        # Get it multiple times
        cache.get_definition("track", "en", "Track the package")
        cache.get_definition("track", "en", "Track the package")
        cache.get_definition("track", "en", "Track the package")
        
        # Verify access count
        cursor = temp_db.conn.cursor()
        context_hash = cache._hash_context("Track the package")
        cursor.execute(
            "SELECT access_count FROM reading_definition_cache WHERE word = ? AND language = ? AND context_hash = ?",
            ("track", "en", context_hash)
        )
        count = cursor.fetchone()[0]
        assert count == 4  # 1 from store + 3 from gets


class TestExpireOldDefinitions:
    """Test expire_old_definitions method."""
    
    def test_expire_old_definitions_removes_old_entries(self, cache, temp_db):
        """Test that old definitions are removed."""
        from datetime import timedelta
        
        # Store a definition
        cache.store_definition(
            word="old",
            language="en",
            context="This is old",
            definition="Not new",
            synonym=None,
            example=None
        )
        
        # Manually update last_accessed to be 31 days ago
        cursor = temp_db.conn.cursor()
        old_date = (datetime.now() - timedelta(days=31)).isoformat()
        cursor.execute("""
            UPDATE reading_definition_cache
            SET last_accessed = ?
            WHERE word = ?
        """, (old_date, "old"))
        temp_db.conn.commit()
        
        # Expire definitions older than 30 days
        removed_count = cache.expire_old_definitions(days=30)
        
        # Verify the definition was removed
        assert removed_count == 1
        result = cache.get_definition("old", "en", "This is old")
        assert result is None
    
    def test_expire_old_definitions_keeps_recent_entries(self, cache, temp_db):
        """Test that recent definitions are not removed."""
        # Store a definition
        cache.store_definition(
            word="recent",
            language="en",
            context="This is recent",
            definition="New",
            synonym=None,
            example=None
        )
        
        # Expire definitions older than 30 days
        removed_count = cache.expire_old_definitions(days=30)
        
        # Verify the definition was not removed
        assert removed_count == 0
        result = cache.get_definition("recent", "en", "This is recent")
        assert result is not None
        assert result['definition'] == "New"
    
    def test_expire_old_definitions_mixed_ages(self, cache, temp_db):
        """Test expiration with mixed old and recent definitions."""
        from datetime import timedelta
        
        # Store multiple definitions
        cache.store_definition(
            word="old1",
            language="en",
            context="Old one",
            definition="Old definition 1",
            synonym=None,
            example=None
        )
        
        cache.store_definition(
            word="old2",
            language="en",
            context="Old two",
            definition="Old definition 2",
            synonym=None,
            example=None
        )
        
        cache.store_definition(
            word="recent",
            language="en",
            context="Recent one",
            definition="Recent definition",
            synonym=None,
            example=None
        )
        
        # Make two definitions old
        cursor = temp_db.conn.cursor()
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        cursor.execute("""
            UPDATE reading_definition_cache
            SET last_accessed = ?
            WHERE word IN (?, ?)
        """, (old_date, "old1", "old2"))
        temp_db.conn.commit()
        
        # Expire definitions older than 30 days
        removed_count = cache.expire_old_definitions(days=30)
        
        # Verify correct number removed
        assert removed_count == 2
        
        # Verify old definitions are gone
        assert cache.get_definition("old1", "en", "Old one") is None
        assert cache.get_definition("old2", "en", "Old two") is None
        
        # Verify recent definition remains
        result = cache.get_definition("recent", "en", "Recent one")
        assert result is not None
        assert result['definition'] == "Recent definition"
    
    def test_expire_old_definitions_custom_days(self, cache, temp_db):
        """Test expiration with custom number of days."""
        from datetime import timedelta
        
        # Store a definition
        cache.store_definition(
            word="custom",
            language="en",
            context="Custom expiry",
            definition="Custom definition",
            synonym=None,
            example=None
        )
        
        # Make it 8 days old
        cursor = temp_db.conn.cursor()
        old_date = (datetime.now() - timedelta(days=8)).isoformat()
        cursor.execute("""
            UPDATE reading_definition_cache
            SET last_accessed = ?
            WHERE word = ?
        """, (old_date, "custom"))
        temp_db.conn.commit()
        
        # Expire with 7 days threshold - should remove
        removed_count = cache.expire_old_definitions(days=7)
        assert removed_count == 1
        assert cache.get_definition("custom", "en", "Custom expiry") is None
    
    def test_expire_old_definitions_empty_cache(self, cache):
        """Test expiration on empty cache returns 0."""
        removed_count = cache.expire_old_definitions(days=30)
        assert removed_count == 0
    
    def test_expire_old_definitions_default_parameter(self, cache, temp_db):
        """Test that default parameter is 30 days."""
        from datetime import timedelta
        
        # Store a definition
        cache.store_definition(
            word="default",
            language="en",
            context="Default test",
            definition="Default definition",
            synonym=None,
            example=None
        )
        
        # Make it 31 days old
        cursor = temp_db.conn.cursor()
        old_date = (datetime.now() - timedelta(days=31)).isoformat()
        cursor.execute("""
            UPDATE reading_definition_cache
            SET last_accessed = ?
            WHERE word = ?
        """, (old_date, "default"))
        temp_db.conn.commit()
        
        # Call without days parameter - should use default of 30
        removed_count = cache.expire_old_definitions()
        assert removed_count == 1
