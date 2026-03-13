"""
Property-based tests for definition required fields in Immersive Reading Mode.

These tests verify that all word definitions returned by ReadingAssistant.get_word_definition()
contain the required fields (word, definition, example) regardless of whether the definition
comes from cache or is newly generated.

Property 14: Definition Contains Required Fields
- Validates: Requirements 4.1, 4.2, 4.4
- Verifies definition contains word, definition, and example fields
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager
from src.features.reader.reading_assistant import ReadingAssistant


class TestDefinitionRequiredFieldsProperty:
    """
    Property 14: Definition Contains Required Fields
    
    This property ensures that every word definition returned by ReadingAssistant.get_word_definition()
    contains all required fields: word, definition, and example. This must hold true regardless of:
    
    1. Whether the definition comes from cache or is newly generated
    2. Whether generation succeeds or fails
    3. The specific word, language, or context used
    
    The property validates:
    - Requirement 4.1: Display contextual definition popup (requires word field)
    - Requirement 4.2: Generate definition using context (requires definition field)
    - Requirement 4.4: Provide example sentence (requires example field)
    
    The property holds for ANY valid word, language, and context combination.
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
    def study_manager(self, db):
        """Create a StudyManager instance."""
        return StudyManager(db)

    @pytest.fixture
    def assistant(self, study_manager, db):
        """Create a ReadingAssistant instance."""
        return ReadingAssistant(study_manager, db)

    @given(
        word=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        sentence_context=st.text(min_size=10, max_size=500),
        paragraph_context=st.text(min_size=0, max_size=1000),
        definition_text=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        synonym=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        example=st.one_of(st.none(), st.text(min_size=5, max_size=200))
    )
    @settings(max_examples=25, deadline=None)
    def test_generated_definition_contains_required_fields(
        self,
        word,
        language,
        sentence_context,
        paragraph_context,
        definition_text,
        synonym,
        example
    ):
        """
        Property test: Generated definitions contain all required fields.
        
        For ANY valid word, language, context, and generated definition content:
        1. Mock StudyManager to return a successful definition
        2. Call get_word_definition()
        3. Verify the result contains 'word', 'definition', and 'example' fields
        4. Verify 'word' matches the input word
        5. Verify 'definition' is not empty
        6. Verify 'example' exists (even if empty string)
        
        This ensures generated definitions always have the required structure.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return successful definition
            suggestions = {}
            if synonym is not None:
                suggestions['synonym'] = synonym
            if example is not None:
                suggestions['example'] = example
            
            assistant.study_manager.generate_word_content = Mock(
                return_value=(True, definition_text, suggestions)
            )
            
            # Get definition
            result = assistant.get_word_definition(
                word=word,
                sentence_context=sentence_context,
                paragraph_context=paragraph_context,
                language=language
            )
            
            # Verify result is not None
            assert result is not None, \
                f"get_word_definition should return a result for word '{word}'"
            
            # Verify required field 'word' exists and matches input
            assert 'word' in result, \
                "Result must contain 'word' field (Requirement 4.1)"
            assert result['word'] == word, \
                f"Word field should match input: expected '{word}', got '{result['word']}'"
            
            # Verify required field 'definition' exists and is not empty
            assert 'definition' in result, \
                "Result must contain 'definition' field (Requirement 4.2)"
            assert result['definition'] is not None, \
                "Definition field must not be None"
            assert len(result['definition']) > 0, \
                "Definition field must not be empty"
            
            # Verify required field 'example' exists (can be empty string)
            assert 'example' in result, \
                "Result must contain 'example' field (Requirement 4.4)"
            assert result['example'] is not None, \
                "Example field must not be None (can be empty string)"
            
            # Verify example is a string
            assert isinstance(result['example'], str), \
                f"Example must be a string, got {type(result['example'])}"
            
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
        sentence_context=st.text(min_size=10, max_size=500),
        paragraph_context=st.text(min_size=0, max_size=1000),
        cached_definition=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        cached_synonym=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        cached_example=st.one_of(st.none(), st.text(min_size=5, max_size=200))
    )
    @settings(max_examples=25, deadline=None)
    def test_cached_definition_contains_required_fields(
        self,
        word,
        language,
        sentence_context,
        paragraph_context,
        cached_definition,
        cached_synonym,
        cached_example
    ):
        """
        Property test: Cached definitions contain all required fields.
        
        For ANY valid word, language, context, and cached definition content:
        1. Pre-populate the cache with a definition
        2. Call get_word_definition()
        3. Verify the result contains 'word', 'definition', and 'example' fields
        4. Verify 'word' matches the input word
        5. Verify 'definition' is not empty
        6. Verify 'example' exists (even if None from cache)
        
        This ensures cached definitions also have the required structure.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Pre-populate cache
            assistant.cache.store_definition(
                word=word,
                language=language,
                context=sentence_context,
                definition=cached_definition,
                synonym=cached_synonym,
                example=cached_example
            )
            
            # Get definition (should come from cache)
            result = assistant.get_word_definition(
                word=word,
                sentence_context=sentence_context,
                paragraph_context=paragraph_context,
                language=language
            )
            
            # Verify result is not None
            assert result is not None, \
                f"get_word_definition should return a result for cached word '{word}'"
            
            # Verify source is cache
            assert result.get('source') == 'cache', \
                "Result should come from cache"
            
            # Verify required field 'word' exists and matches input
            assert 'word' in result, \
                "Cached result must contain 'word' field (Requirement 4.1)"
            assert result['word'] == word, \
                f"Word field should match input: expected '{word}', got '{result['word']}'"
            
            # Verify required field 'definition' exists and is not empty
            assert 'definition' in result, \
                "Cached result must contain 'definition' field (Requirement 4.2)"
            assert result['definition'] is not None, \
                "Definition field must not be None"
            assert len(result['definition']) > 0, \
                "Definition field must not be empty"
            
            # Verify required field 'example' exists
            assert 'example' in result, \
                "Cached result must contain 'example' field (Requirement 4.4)"
            # Note: example can be None from cache, but field must exist
            
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
        sentence_context=st.text(min_size=10, max_size=500),
        paragraph_context=st.text(min_size=0, max_size=1000),
        error_message=st.text(min_size=5, max_size=200).filter(lambda x: x.strip() != '')
    )
    @settings(max_examples=20, deadline=None)
    def test_failed_definition_contains_required_fields(
        self,
        word,
        language,
        sentence_context,
        paragraph_context,
        error_message
    ):
        """
        Property test: Failed definitions still contain all required fields.
        
        For ANY valid word, language, context, and error condition:
        1. Mock StudyManager to return a failed definition
        2. Call get_word_definition()
        3. Verify the result contains 'word', 'definition', and 'example' fields
        4. Verify 'word' matches the input word
        5. Verify 'definition' contains the error message
        6. Verify 'example' exists (should be empty string for errors)
        
        This ensures even error cases maintain the required structure.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return failed definition
            assistant.study_manager.generate_word_content = Mock(
                return_value=(False, error_message, {})
            )
            
            # Get definition
            result = assistant.get_word_definition(
                word=word,
                sentence_context=sentence_context,
                paragraph_context=paragraph_context,
                language=language
            )
            
            # Verify result is not None
            assert result is not None, \
                f"get_word_definition should return a result even on failure for word '{word}'"
            
            # Verify source is error
            assert result.get('source') == 'error', \
                "Result should have source='error' for failed generation"
            
            # Verify required field 'word' exists and matches input
            assert 'word' in result, \
                "Error result must contain 'word' field (Requirement 4.1)"
            assert result['word'] == word, \
                f"Word field should match input: expected '{word}', got '{result['word']}'"
            
            # Verify required field 'definition' exists (contains error message)
            assert 'definition' in result, \
                "Error result must contain 'definition' field (Requirement 4.2)"
            assert result['definition'] is not None, \
                "Definition field must not be None even on error"
            assert len(result['definition']) > 0, \
                "Definition field must contain error message"
            
            # Verify required field 'example' exists
            assert 'example' in result, \
                "Error result must contain 'example' field (Requirement 4.4)"
            assert result['example'] is not None, \
                "Example field must not be None (should be empty string for errors)"
            assert result['example'] == '', \
                "Example should be empty string for error cases"
            
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

    def test_definition_fields_are_strings(self):
        """
        Test that all required fields are strings (not a property test, but validates type safety).
        
        Verifies that word, definition, and example fields are always strings,
        never other types like None, int, list, etc.
        """
        # Create temporary database
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock successful generation
            assistant.study_manager.generate_word_content = Mock(
                return_value=(True, "A test definition", {'example': 'Test example'})
            )
            
            result = assistant.get_word_definition(
                word="test",
                sentence_context="This is a test.",
                paragraph_context="",
                language="en"
            )
            
            # Verify all required fields are strings
            assert isinstance(result['word'], str), \
                f"'word' must be a string, got {type(result['word'])}"
            assert isinstance(result['definition'], str), \
                f"'definition' must be a string, got {type(result['definition'])}"
            assert isinstance(result['example'], str), \
                f"'example' must be a string, got {type(result['example'])}"
            
        finally:
            db.close()
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    def test_definition_with_missing_example_in_suggestions(self):
        """
        Test that when suggestions don't include example, definition is used as fallback.
        
        This validates the fallback behavior documented in the implementation.
        """
        # Create temporary database
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock generation with no example in suggestions
            definition_text = "A test definition"
            assistant.study_manager.generate_word_content = Mock(
                return_value=(True, definition_text, {'synonym': 'check'})
            )
            
            result = assistant.get_word_definition(
                word="test",
                sentence_context="This is a test.",
                paragraph_context="",
                language="en"
            )
            
            # Verify example field exists and uses definition as fallback
            assert 'example' in result
            assert result['example'] == definition_text, \
                "Example should use definition as fallback when not in suggestions"
            
        finally:
            db.close()
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    @given(
        words=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
            min_size=1,
            max_size=10,
            unique=True
        ),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500)
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_definitions_all_have_required_fields(
        self,
        words,
        language,
        context
    ):
        """
        Property test: Multiple definitions all contain required fields.
        
        For ANY list of words, language, and context:
        1. Generate definitions for all words
        2. Verify each result contains all required fields
        
        This ensures the property holds across multiple lookups in sequence.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return successful definitions
            assistant.study_manager.generate_word_content = Mock(
                return_value=(True, "A definition", {'example': 'An example'})
            )
            
            # Get definitions for all words
            results = []
            for word in words:
                result = assistant.get_word_definition(
                    word=word,
                    sentence_context=context,
                    paragraph_context="",
                    language=language
                )
                results.append(result)
            
            # Verify all results have required fields
            for i, result in enumerate(results):
                assert result is not None, \
                    f"Result {i} should not be None"
                
                assert 'word' in result, \
                    f"Result {i} must contain 'word' field"
                assert result['word'] == words[i], \
                    f"Result {i} word mismatch"
                
                assert 'definition' in result, \
                    f"Result {i} must contain 'definition' field"
                assert len(result['definition']) > 0, \
                    f"Result {i} definition must not be empty"
                
                assert 'example' in result, \
                    f"Result {i} must contain 'example' field"
                assert result['example'] is not None, \
                    f"Result {i} example must not be None"
            
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
