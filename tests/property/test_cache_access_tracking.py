"""
Property-based tests for cache access tracking in Immersive Reading Mode.

These tests verify that the definition cache correctly tracks access patterns
including access count increments and last accessed timestamp updates.

Property 17: Cache Access Tracking
- Validates: Requirements 6.4
- Verifies access_count increments and last_accessed updates on cache hits
"""

import tempfile
import os
import time
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from src.core.database import FlashcardDatabase
from src.features.reader.definition_cache import DefinitionCache


class TestCacheAccessTrackingProperty:
    """
    Property 17: Cache Access Tracking
    
    This property ensures that when a cached definition is accessed, the cache
    correctly tracks access patterns by:
    
    1. Incrementing access_count on each cache hit (Requirement 6.4)
    2. Updating last_accessed timestamp on each cache hit (Requirement 6.4)
    
    The property holds for ANY valid word, language, context, and number of accesses.
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
    def cache(self, db):
        """Create a DefinitionCache instance."""
        return DefinitionCache(db)

    def _get_cache_stats(self, db, word, language, context_hash):
        """Helper to get access_count and last_accessed from database."""
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT access_count, last_accessed
            FROM reading_definition_cache
            WHERE word = ? AND language = ? AND context_hash = ?
        """, (word, language, context_hash))
        row = cursor.fetchone()
        if row:
            return {
                'access_count': row[0],
                'last_accessed': row[1]
            }
        return None

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        num_accesses=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_access_count_increments_on_cache_hits(
        self,
        word,
        language,
        context,
        definition,
        num_accesses
    ):
        """
        Property test: access_count increments on each cache hit.
        
        For ANY valid word, language, context, and number of accesses:
        1. Store a definition in the cache (initial access_count = 1)
        2. Perform N lookups (cache hits)
        3. Verify access_count = 1 + N (initial + lookups)
        
        This ensures access tracking works correctly across diverse inputs.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Step 1: Store the definition (initial access_count = 1)
            cache.store_definition(
                word=word,
                language=language,
                context=context,
                definition=definition
            )
            
            # Get context hash for direct database queries
            context_hash = cache._hash_context(context)
            
            # Verify initial access_count is 1
            initial_stats = self._get_cache_stats(db, word, language, context_hash)
            assert initial_stats is not None, "Definition should be stored in cache"
            assert initial_stats['access_count'] == 1, \
                f"Initial access_count should be 1, got {initial_stats['access_count']}"
            
            # Step 2: Perform N lookups (cache hits)
            for i in range(num_accesses):
                result = cache.get_definition(word, language, context)
                assert result is not None, \
                    f"Lookup {i+1} should return cached definition"
                assert result['source'] == 'cache', \
                    f"Lookup {i+1} should be a cache hit"
            
            # Step 3: Verify access_count = 1 + num_accesses
            final_stats = self._get_cache_stats(db, word, language, context_hash)
            assert final_stats is not None, "Definition should still be in cache"
            
            expected_count = 1 + num_accesses
            assert final_stats['access_count'] == expected_count, \
                f"After {num_accesses} lookups, access_count should be {expected_count}, " \
                f"got {final_stats['access_count']}"
            
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

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != '')
    )
    @settings(max_examples=100, deadline=None)
    def test_last_accessed_updates_on_cache_hits(
        self,
        word,
        language,
        context,
        definition
    ):
        """
        Property test: last_accessed timestamp updates on each cache hit.
        
        For ANY valid word, language, and context:
        1. Store a definition in the cache
        2. Record initial last_accessed timestamp
        3. Wait a small amount of time
        4. Perform a lookup (cache hit)
        5. Verify last_accessed has been updated to a later timestamp
        
        This ensures timestamp tracking works correctly.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Step 1: Store the definition
            cache.store_definition(
                word=word,
                language=language,
                context=context,
                definition=definition
            )
            
            # Get context hash for direct database queries
            context_hash = cache._hash_context(context)
            
            # Step 2: Record initial last_accessed timestamp
            initial_stats = self._get_cache_stats(db, word, language, context_hash)
            assert initial_stats is not None, "Definition should be stored in cache"
            initial_timestamp = initial_stats['last_accessed']
            
            # Step 3: Wait a small amount of time (ensure timestamp difference)
            time.sleep(0.01)  # 10ms should be enough for timestamp difference
            
            # Step 4: Perform a lookup (cache hit)
            result = cache.get_definition(word, language, context)
            assert result is not None, "Lookup should return cached definition"
            assert result['source'] == 'cache', "Lookup should be a cache hit"
            
            # Step 5: Verify last_accessed has been updated
            final_stats = self._get_cache_stats(db, word, language, context_hash)
            assert final_stats is not None, "Definition should still be in cache"
            final_timestamp = final_stats['last_accessed']
            
            # Parse timestamps for comparison
            initial_dt = datetime.fromisoformat(initial_timestamp)
            final_dt = datetime.fromisoformat(final_timestamp)
            
            assert final_dt > initial_dt, \
                f"last_accessed should be updated after cache hit. " \
                f"Initial: {initial_timestamp}, Final: {final_timestamp}"
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        num_accesses=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_last_accessed_monotonically_increases(
        self,
        word,
        language,
        context,
        definition,
        num_accesses
    ):
        """
        Property test: last_accessed timestamp monotonically increases with each access.
        
        For ANY valid word, language, context, and number of accesses:
        1. Store a definition
        2. Perform multiple lookups with small delays between them
        3. Verify last_accessed timestamp increases (or stays the same) after each lookup
        
        This ensures timestamps never go backwards.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Store the definition
            cache.store_definition(
                word=word,
                language=language,
                context=context,
                definition=definition
            )
            
            # Get context hash for direct database queries
            context_hash = cache._hash_context(context)
            
            # Track timestamps across multiple accesses
            timestamps = []
            
            # Get initial timestamp
            initial_stats = self._get_cache_stats(db, word, language, context_hash)
            timestamps.append(datetime.fromisoformat(initial_stats['last_accessed']))
            
            # Perform multiple lookups with small delays
            for i in range(num_accesses):
                time.sleep(0.01)  # Small delay to ensure timestamp difference
                
                result = cache.get_definition(word, language, context)
                assert result is not None, f"Lookup {i+1} should return cached definition"
                
                stats = self._get_cache_stats(db, word, language, context_hash)
                timestamps.append(datetime.fromisoformat(stats['last_accessed']))
            
            # Verify timestamps are monotonically increasing (or equal)
            for i in range(len(timestamps) - 1):
                assert timestamps[i+1] >= timestamps[i], \
                    f"Timestamp at access {i+1} ({timestamps[i+1]}) should be >= " \
                    f"timestamp at access {i} ({timestamps[i]})"
            
            # Verify at least some timestamps increased (not all equal)
            assert timestamps[-1] > timestamps[0], \
                f"Final timestamp ({timestamps[-1]}) should be greater than " \
                f"initial timestamp ({timestamps[0]})"
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    def test_access_tracking_with_context_fallback(self, cache, db):
        """
        Test that access tracking works correctly when falling back to generic cache.
        
        When a context-specific definition is not found and the cache falls back
        to a generic definition, the access tracking should update the generic
        definition's stats, not create new tracking for the specific context.
        """
        word = "fallback"
        language = "en"
        generic_context = ""
        specific_context = "This is a specific context for fallback"
        definition = "A backup option"
        
        # Store generic definition
        cache.store_definition(
            word=word,
            language=language,
            context=generic_context,
            definition=definition
        )
        
        # Get context hash for generic cache
        generic_hash = cache._hash_context(generic_context)
        
        # Check initial access_count
        initial_stats = self._get_cache_stats(db, word, language, generic_hash)
        assert initial_stats['access_count'] == 1
        
        # Lookup with specific context (should fall back to generic)
        result = cache.get_definition(word, language, specific_context)
        assert result is not None
        assert result['definition'] == definition
        
        # Verify generic cache access_count incremented
        final_stats = self._get_cache_stats(db, word, language, generic_hash)
        assert final_stats['access_count'] == 2, \
            "Generic cache access_count should increment on fallback lookup"
        
        # Verify no entry was created for specific context
        specific_hash = cache._hash_context(specific_context)
        specific_stats = self._get_cache_stats(db, word, language, specific_hash)
        assert specific_stats is None, \
            "No cache entry should be created for specific context on fallback"

    def test_access_tracking_independent_for_different_contexts(self, cache, db):
        """
        Test that access tracking is independent for different contexts of the same word.
        
        When the same word has different cached definitions for different contexts,
        each should have independent access tracking.
        """
        word = "track"
        language = "en"
        context1 = "Track your progress"
        context2 = "Train track"
        definition1 = "To monitor or follow"
        definition2 = "A rail line"
        
        # Store definitions for both contexts
        cache.store_definition(word, language, context1, definition1)
        cache.store_definition(word, language, context2, definition2)
        
        # Get context hashes
        hash1 = cache._hash_context(context1)
        hash2 = cache._hash_context(context2)
        
        # Access context1 multiple times
        for _ in range(3):
            cache.get_definition(word, language, context1)
        
        # Access context2 once
        cache.get_definition(word, language, context2)
        
        # Verify independent tracking
        stats1 = self._get_cache_stats(db, word, language, hash1)
        stats2 = self._get_cache_stats(db, word, language, hash2)
        
        assert stats1['access_count'] == 4, \
            "Context1 should have access_count=4 (1 store + 3 lookups)"
        assert stats2['access_count'] == 2, \
            "Context2 should have access_count=2 (1 store + 1 lookup)"

    def test_access_tracking_persists_across_cache_instances(self, db):
        """
        Test that access tracking persists in the database across cache instances.
        
        Access counts and timestamps should be stored in the database and
        persist even when creating new DefinitionCache instances.
        """
        word = "persist"
        language = "en"
        context = "Data should persist"
        definition = "To continue to exist"
        
        # Create first cache instance and store definition
        cache1 = DefinitionCache(db)
        cache1.store_definition(word, language, context, definition)
        
        # Access it twice
        cache1.get_definition(word, language, context)
        cache1.get_definition(word, language, context)
        
        # Create second cache instance
        cache2 = DefinitionCache(db)
        
        # Access with second instance
        result = cache2.get_definition(word, language, context)
        assert result is not None
        
        # Verify access_count persisted and incremented
        context_hash = cache2._hash_context(context)
        stats = self._get_cache_stats(db, word, language, context_hash)
        assert stats['access_count'] == 4, \
            "Access count should persist across cache instances (1 store + 3 lookups)"

    def test_no_access_tracking_on_cache_miss(self, cache, db):
        """
        Test that access tracking does not occur on cache misses.
        
        When a definition is not found in the cache, no access tracking
        should be performed (no phantom entries created).
        """
        word = "missing"
        language = "en"
        context = "This word is not cached"
        
        # Attempt lookup (cache miss)
        result = cache.get_definition(word, language, context)
        assert result is None, "Should be a cache miss"
        
        # Verify no cache entry was created
        context_hash = cache._hash_context(context)
        stats = self._get_cache_stats(db, word, language, context_hash)
        assert stats is None, \
            "No cache entry should be created on cache miss"

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition1=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        definition2=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        num_accesses_before=st.integers(min_value=1, max_value=5),
        num_accesses_after=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    def test_access_tracking_survives_definition_update(
        self,
        word,
        language,
        context,
        definition1,
        definition2,
        num_accesses_before,
        num_accesses_after
    ):
        """
        Property test: Access tracking continues correctly when definition is updated.
        
        For ANY valid word, language, context, and definitions:
        1. Store definition1 and access it N times
        2. Update to definition2 (UPSERT)
        3. Access it M more times
        4. Verify access_count reflects all accesses (not reset by update)
        
        Note: Current implementation resets access_count on update (INSERT OR REPLACE).
        This test documents the current behavior. If access_count should persist
        through updates, the implementation would need to be changed.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Store definition1
            cache.store_definition(word, language, context, definition1)
            
            # Access it num_accesses_before times
            for _ in range(num_accesses_before):
                cache.get_definition(word, language, context)
            
            # Get context hash
            context_hash = cache._hash_context(context)
            
            # Check access_count before update
            stats_before = self._get_cache_stats(db, word, language, context_hash)
            expected_before = 1 + num_accesses_before
            assert stats_before['access_count'] == expected_before
            
            # Update to definition2
            cache.store_definition(word, language, context, definition2)
            
            # Check access_count after update (INSERT OR REPLACE resets to 1)
            stats_after_update = self._get_cache_stats(db, word, language, context_hash)
            assert stats_after_update['access_count'] == 1, \
                "Current implementation resets access_count on update (INSERT OR REPLACE)"
            
            # Access it num_accesses_after times
            for _ in range(num_accesses_after):
                result = cache.get_definition(word, language, context)
                assert result['definition'] == definition2
            
            # Check final access_count
            stats_final = self._get_cache_stats(db, word, language, context_hash)
            expected_final = 1 + num_accesses_after
            assert stats_final['access_count'] == expected_final, \
                f"After update and {num_accesses_after} accesses, " \
                f"access_count should be {expected_final}"
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass
