"""
Property-based tests for definition caching in Immersive Reading Mode.

These tests verify that the definition caching system correctly stores and
retrieves definitions, reducing redundant LLM API calls and improving performance.

Property 16: Definition Caching
- Validates: Requirements 6.1, 6.2, 6.3
- Verifies generated definitions are cached and subsequent lookups return cached version
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.core.database import FlashcardDatabase
from src.features.reader.definition_cache import DefinitionCache


class TestDefinitionCachingProperty:
    """
    Property 16: Definition Caching
    
    This property ensures that when a definition is generated and stored in the cache,
    subsequent lookups for the same word, language, and context return the cached
    version instead of requiring a new generation. This validates:
    
    1. Definitions are correctly stored in the cache (Requirement 6.1)
    2. Cache lookups check for existing definitions before generation (Requirement 6.2)
    3. Context-specific caching works correctly with fallback to generic cache (Requirement 6.3)
    
    The property holds for ANY valid word, language, context, and definition content.
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

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        synonym=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        example=st.one_of(st.none(), st.text(min_size=5, max_size=200))
    )
    @settings(max_examples=100, deadline=None)
    def test_definition_is_cached_and_retrieved(
        self,
        word,
        language,
        context,
        definition,
        synonym,
        example
    ):
        """
        Property test: Definitions are cached and subsequent lookups return cached version.
        
        For ANY valid word, language, context, and definition:
        1. Store the definition in the cache
        2. Retrieve the definition with the same word, language, and context
        3. Verify the retrieved definition matches the stored definition
        4. Verify the source is marked as 'cache'
        5. Retrieve again and verify it still returns the cached version
        
        This ensures the caching mechanism works correctly across diverse inputs.
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
                definition=definition,
                synonym=synonym,
                example=example
            )
            
            # Step 2: Retrieve the definition (first lookup)
            result1 = cache.get_definition(word, language, context)
            
            # Step 3: Verify the retrieved definition matches
            assert result1 is not None, \
                f"Definition for word '{word}' should be found in cache"
            
            assert result1['word'] == word, \
                f"Cached word mismatch: expected '{word}', got '{result1['word']}'"
            
            assert result1['definition'] == definition, \
                f"Cached definition mismatch: expected '{definition}', got '{result1['definition']}'"
            
            assert result1['synonym'] == synonym, \
                f"Cached synonym mismatch: expected '{synonym}', got '{result1['synonym']}'"
            
            assert result1['example'] == example, \
                f"Cached example mismatch: expected '{example}', got '{result1['example']}'"
            
            # Step 4: Verify source is marked as 'cache'
            assert result1['source'] == 'cache', \
                f"Source should be 'cache', got '{result1['source']}'"
            
            # Step 5: Retrieve again (second lookup)
            result2 = cache.get_definition(word, language, context)
            
            # Verify second lookup also returns cached version
            assert result2 is not None, \
                "Second lookup should also return cached definition"
            
            assert result2['word'] == word
            assert result2['definition'] == definition
            assert result2['synonym'] == synonym
            assert result2['example'] == example
            assert result2['source'] == 'cache'
            
            # Verify both lookups return identical data
            assert result1 == result2, \
                "Multiple cache lookups should return identical data"
            
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
        context1=st.text(min_size=10, max_size=500),
        context2=st.text(min_size=10, max_size=500),
        definition1=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        definition2=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != '')
    )
    @settings(max_examples=50, deadline=None)
    def test_context_specific_caching(
        self,
        word,
        language,
        context1,
        context2,
        definition1,
        definition2
    ):
        """
        Property test: Context-specific caching stores different definitions for different contexts.
        
        For ANY valid word, language, and two different contexts:
        1. Store definition1 with context1
        2. Store definition2 with context2
        3. Retrieve with context1 and verify it returns definition1
        4. Retrieve with context2 and verify it returns definition2
        
        This ensures context-specific caching works correctly (Requirement 6.3).
        """
        # Ensure contexts are different
        assume(context1 != context2)
        
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Store definition with context1
            cache.store_definition(
                word=word,
                language=language,
                context=context1,
                definition=definition1,
                synonym=None,
                example=None
            )
            
            # Store definition with context2
            cache.store_definition(
                word=word,
                language=language,
                context=context2,
                definition=definition2,
                synonym=None,
                example=None
            )
            
            # Retrieve with context1
            result1 = cache.get_definition(word, language, context1)
            assert result1 is not None
            assert result1['definition'] == definition1, \
                f"Context1 should return definition1, got '{result1['definition']}'"
            
            # Retrieve with context2
            result2 = cache.get_definition(word, language, context2)
            assert result2 is not None
            assert result2['definition'] == definition2, \
                f"Context2 should return definition2, got '{result2['definition']}'"
            
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
        generic_definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        lookup_context=st.text(min_size=10, max_size=500)
    )
    @settings(max_examples=50, deadline=None)
    def test_fallback_to_generic_cache(
        self,
        word,
        language,
        generic_definition,
        lookup_context
    ):
        """
        Property test: Cache falls back to generic definition when context-specific not found.
        
        For ANY valid word, language, and contexts:
        1. Store a generic definition (empty context)
        2. Lookup with a different context
        3. Verify it returns the generic definition as fallback
        
        This validates Requirement 6.3: fallback to generic cache.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Store generic definition (empty context)
            cache.store_definition(
                word=word,
                language=language,
                context="",  # Generic cache
                definition=generic_definition,
                synonym=None,
                example=None
            )
            
            # Lookup with different context (should fall back to generic)
            result = cache.get_definition(word, language, lookup_context)
            
            assert result is not None, \
                "Should find generic definition as fallback"
            
            assert result['definition'] == generic_definition, \
                f"Should return generic definition, got '{result['definition']}'"
            
            assert result['source'] == 'cache', \
                "Source should still be 'cache' for fallback"
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    def test_cache_miss_returns_none(self, cache):
        """
        Test that cache miss returns None (not a property test, but validates expected behavior).
        
        When a definition is not in the cache, get_definition should return None,
        indicating that generation is needed.
        """
        result = cache.get_definition("nonexistent", "en", "Some context")
        assert result is None, "Cache miss should return None"

    def test_multiple_words_cached_independently(self, cache):
        """
        Test that multiple words can be cached independently.
        
        Verifies that caching one word doesn't interfere with caching another word.
        """
        # Store definitions for multiple words
        words_data = [
            {
                'word': 'hello',
                'language': 'en',
                'context': 'Hello world',
                'definition': 'A greeting'
            },
            {
                'word': 'goodbye',
                'language': 'en',
                'context': 'Goodbye friend',
                'definition': 'A farewell'
            },
            {
                'word': 'thanks',
                'language': 'en',
                'context': 'Thanks for helping',
                'definition': 'Expression of gratitude'
            }
        ]
        
        # Store all definitions
        for data in words_data:
            cache.store_definition(
                word=data['word'],
                language=data['language'],
                context=data['context'],
                definition=data['definition']
            )
        
        # Retrieve and verify each definition
        for data in words_data:
            result = cache.get_definition(
                data['word'],
                data['language'],
                data['context']
            )
            assert result is not None
            assert result['word'] == data['word']
            assert result['definition'] == data['definition']
            assert result['source'] == 'cache'

    def test_cache_update_replaces_existing_definition(self, cache):
        """
        Test that storing a definition with same word/language/context updates the existing one.
        
        This validates that the cache uses UPSERT behavior.
        """
        word = "update"
        language = "en"
        context = "Update the system"
        
        # Store initial definition
        cache.store_definition(
            word=word,
            language=language,
            context=context,
            definition="Old definition"
        )
        
        # Retrieve and verify
        result1 = cache.get_definition(word, language, context)
        assert result1['definition'] == "Old definition"
        
        # Store updated definition
        cache.store_definition(
            word=word,
            language=language,
            context=context,
            definition="New definition",
            synonym="refresh",
            example="Update your software"
        )
        
        # Retrieve and verify updated definition
        result2 = cache.get_definition(word, language, context)
        assert result2['definition'] == "New definition"
        assert result2['synonym'] == "refresh"
        assert result2['example'] == "Update your software"

    def test_cache_works_across_multiple_languages(self, cache):
        """
        Test that caching works correctly for the same word in different languages.
        
        Verifies that language is part of the cache key.
        """
        word = "book"
        context = "I read a book"
        
        # Store definitions in different languages
        cache.store_definition(
            word=word,
            language='en',
            context=context,
            definition='A written work'
        )
        
        cache.store_definition(
            word=word,
            language='es',
            context=context,
            definition='Un trabajo escrito'
        )
        
        # Retrieve English definition
        result_en = cache.get_definition(word, 'en', context)
        assert result_en['definition'] == 'A written work'
        
        # Retrieve Spanish definition
        result_es = cache.get_definition(word, 'es', context)
        assert result_es['definition'] == 'Un trabajo escrito'

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500),
        definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        num_lookups=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_repeated_lookups_return_same_cached_definition(
        self,
        word,
        language,
        context,
        definition,
        num_lookups
    ):
        """
        Property test: Repeated lookups always return the same cached definition.
        
        For ANY valid word, language, context, and number of lookups:
        1. Store a definition
        2. Perform multiple lookups
        3. Verify all lookups return identical cached data
        
        This ensures cache consistency across multiple accesses.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and cache
            db = FlashcardDatabase(db_name=temp_db_path)
            cache = DefinitionCache(db)
            
            # Store definition
            cache.store_definition(
                word=word,
                language=language,
                context=context,
                definition=definition
            )
            
            # Perform multiple lookups
            results = []
            for _ in range(num_lookups):
                result = cache.get_definition(word, language, context)
                results.append(result)
            
            # Verify all results are not None
            assert all(r is not None for r in results), \
                "All lookups should return cached definition"
            
            # Verify all results are identical
            first_result = results[0]
            for i, result in enumerate(results[1:], start=2):
                assert result == first_result, \
                    f"Lookup {i} returned different data than first lookup"
            
            # Verify all have correct source
            assert all(r['source'] == 'cache' for r in results), \
                "All lookups should have source='cache'"
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass
