"""
Property-based tests for sentence explanation required fields in Immersive Reading Mode.

These tests verify that all sentence explanations returned by ReadingAssistant.get_sentence_explanation()
contain the required fields (sentence, translation, difficulty) regardless of whether the explanation
generation succeeds or fails.

Property 15: Sentence Explanation Contains Required Fields
- Validates: Requirements 5.1, 5.2, 5.5
- Verifies explanation contains sentence, translation, and difficulty fields
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager
from src.features.reader.reading_assistant import ReadingAssistant


class TestSentenceExplanationRequiredFieldsProperty:
    """
    Property 15: Sentence Explanation Contains Required Fields
    
    This property ensures that every sentence explanation returned by 
    ReadingAssistant.get_sentence_explanation() contains all required fields: 
    sentence, translation, and difficulty. This must hold true regardless of:
    
    1. Whether generation succeeds or fails
    2. The specific sentence, language, or context used
    3. The complexity or length of the sentence
    
    The property validates:
    - Requirement 5.1: Display sentence explanation panel (requires sentence field)
    - Requirement 5.2: Provide literal translation to native language (requires translation field)
    - Requirement 5.5: Indicate difficulty level of the sentence (requires difficulty field)
    
    The property holds for ANY valid sentence, language, and context combination.
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
        sentence=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        native_language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        paragraph_context=st.text(min_size=0, max_size=1000),
        translation_text=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        grammar_notes=st.lists(st.text(min_size=5, max_size=200), min_size=0, max_size=5)
    )
    @settings(max_examples=25, deadline=None)
    def test_generated_explanation_contains_required_fields(
        self,
        sentence,
        language,
        native_language,
        paragraph_context,
        translation_text,
        grammar_notes
    ):
        """
        Property test: Generated sentence explanations contain all required fields.
        
        For ANY valid sentence, language, context, and generated explanation content:
        1. Mock StudyManager to return a successful explanation
        2. Call get_sentence_explanation()
        3. Verify the result contains 'sentence', 'translation', and 'difficulty' fields
        4. Verify 'sentence' matches the input sentence
        5. Verify 'translation' is not empty
        6. Verify 'difficulty' is one of the valid values
        
        This ensures generated explanations always have the required structure.
        
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return successful explanation
            explanation_text = f"**Translation:**\n{translation_text}\n\n**Grammar:**\n" + "\n".join(grammar_notes)
            suggestions = {
                'grammar': grammar_notes
            }
            
            assistant.study_manager.generate_sentence_explanation = Mock(
                return_value=(True, explanation_text, suggestions)
            )
            
            # Get explanation
            result = assistant.get_sentence_explanation(
                sentence=sentence,
                paragraph_context=paragraph_context,
                language=language,
                native_language=native_language
            )
            
            # Verify result is not None
            assert result is not None, \
                f"get_sentence_explanation should return a result for sentence '{sentence[:50]}...'"
            
            # Verify required field 'sentence' exists and matches input (Requirement 5.1)
            assert 'sentence' in result, \
                "Result must contain 'sentence' field (Requirement 5.1)"
            assert result['sentence'] == sentence, \
                f"Sentence field should match input"
            
            # Verify required field 'translation' exists and is not empty (Requirement 5.2)
            assert 'translation' in result, \
                "Result must contain 'translation' field (Requirement 5.2)"
            assert result['translation'] is not None, \
                "Translation field must not be None"
            assert len(result['translation']) > 0, \
                "Translation field must not be empty"
            assert isinstance(result['translation'], str), \
                f"Translation must be a string, got {type(result['translation'])}"
            
            # Verify required field 'difficulty' exists and has valid value (Requirement 5.5)
            assert 'difficulty' in result, \
                "Result must contain 'difficulty' field (Requirement 5.5)"
            assert result['difficulty'] is not None, \
                "Difficulty field must not be None"
            assert result['difficulty'] in ['beginner', 'intermediate', 'advanced', 'unknown'], \
                f"Difficulty must be one of ['beginner', 'intermediate', 'advanced', 'unknown'], got '{result['difficulty']}'"
            
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
        sentence=st.text(min_size=5, max_size=500).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        native_language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        paragraph_context=st.text(min_size=0, max_size=1000),
        error_message=st.text(min_size=5, max_size=200).filter(lambda x: x.strip() != '')
    )
    @settings(max_examples=20, deadline=None)
    def test_failed_explanation_contains_required_fields(
        self,
        sentence,
        language,
        native_language,
        paragraph_context,
        error_message
    ):
        """
        Property test: Failed sentence explanations still contain all required fields.
        
        For ANY valid sentence, language, context, and error condition:
        1. Mock StudyManager to return a failed explanation
        2. Call get_sentence_explanation()
        3. Verify the result contains 'sentence', 'translation', and 'difficulty' fields
        4. Verify 'sentence' matches the input sentence
        5. Verify 'translation' contains the error message
        6. Verify 'difficulty' is 'unknown' for error cases
        
        This ensures even error cases maintain the required structure.
        
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return failed explanation
            assistant.study_manager.generate_sentence_explanation = Mock(
                return_value=(False, error_message, {})
            )
            
            # Get explanation
            result = assistant.get_sentence_explanation(
                sentence=sentence,
                paragraph_context=paragraph_context,
                language=language,
                native_language=native_language
            )
            
            # Verify result is not None
            assert result is not None, \
                f"get_sentence_explanation should return a result even on failure for sentence '{sentence[:50]}...'"
            
            # Verify required field 'sentence' exists and matches input (Requirement 5.1)
            assert 'sentence' in result, \
                "Error result must contain 'sentence' field (Requirement 5.1)"
            assert result['sentence'] == sentence, \
                f"Sentence field should match input even on error"
            
            # Verify required field 'translation' exists (contains error message) (Requirement 5.2)
            assert 'translation' in result, \
                "Error result must contain 'translation' field (Requirement 5.2)"
            assert result['translation'] is not None, \
                "Translation field must not be None even on error"
            assert len(result['translation']) > 0, \
                "Translation field must contain error message"
            assert isinstance(result['translation'], str), \
                f"Translation must be a string, got {type(result['translation'])}"
            
            # Verify required field 'difficulty' exists and is 'unknown' for errors (Requirement 5.5)
            assert 'difficulty' in result, \
                "Error result must contain 'difficulty' field (Requirement 5.5)"
            assert result['difficulty'] == 'unknown', \
                f"Difficulty should be 'unknown' for error cases, got '{result['difficulty']}'"
            
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
        sentences=st.lists(
            st.text(min_size=5, max_size=200).filter(lambda x: x.strip() != ''),
            min_size=1,
            max_size=5,
            unique=True
        ),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        native_language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        context=st.text(min_size=10, max_size=500)
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_explanations_all_have_required_fields(
        self,
        sentences,
        language,
        native_language,
        context
    ):
        """
        Property test: Multiple sentence explanations all contain required fields.
        
        For ANY list of sentences, language, and context:
        1. Generate explanations for all sentences
        2. Verify each result contains all required fields
        
        This ensures the property holds across multiple lookups in sequence.
        
        **Validates: Requirements 5.1, 5.2, 5.5**
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager to return successful explanations
            assistant.study_manager.generate_sentence_explanation = Mock(
                return_value=(True, "**Translation:**\nA translation\n\n**Grammar:**\nSome grammar notes", {'grammar': ['Note 1']})
            )
            
            # Get explanations for all sentences
            results = []
            for sentence in sentences:
                result = assistant.get_sentence_explanation(
                    sentence=sentence,
                    paragraph_context=context,
                    language=language,
                    native_language=native_language
                )
                results.append(result)
            
            # Verify all results have required fields
            for i, result in enumerate(results):
                assert result is not None, \
                    f"Result {i} should not be None"
                
                assert 'sentence' in result, \
                    f"Result {i} must contain 'sentence' field (Requirement 5.1)"
                assert result['sentence'] == sentences[i], \
                    f"Result {i} sentence mismatch"
                
                assert 'translation' in result, \
                    f"Result {i} must contain 'translation' field (Requirement 5.2)"
                assert len(result['translation']) > 0, \
                    f"Result {i} translation must not be empty"
                assert isinstance(result['translation'], str), \
                    f"Result {i} translation must be a string"
                
                assert 'difficulty' in result, \
                    f"Result {i} must contain 'difficulty' field (Requirement 5.5)"
                assert result['difficulty'] in ['beginner', 'intermediate', 'advanced', 'unknown'], \
                    f"Result {i} difficulty must be valid value"
            
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

    def test_explanation_fields_are_correct_types(self):
        """
        Test that all required fields have correct types (not a property test, but validates type safety).
        
        Verifies that sentence, translation, and difficulty fields are always strings,
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
            assistant.study_manager.generate_sentence_explanation = Mock(
                return_value=(True, "**Translation:**\nThis is a test sentence.\n\n**Grammar:**\nSimple present tense.", {'grammar': ['Present tense']})
            )
            
            result = assistant.get_sentence_explanation(
                sentence="This is a test.",
                paragraph_context="This is a test. It is simple.",
                language="en",
                native_language="ko"
            )
            
            # Verify all required fields are strings
            assert isinstance(result['sentence'], str), \
                f"'sentence' must be a string, got {type(result['sentence'])}"
            assert isinstance(result['translation'], str), \
                f"'translation' must be a string, got {type(result['translation'])}"
            assert isinstance(result['difficulty'], str), \
                f"'difficulty' must be a string, got {type(result['difficulty'])}"
            
        finally:
            db.close()
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    @given(
        sentence=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        native_language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh'])
    )
    @settings(max_examples=20, deadline=None)
    def test_difficulty_based_on_sentence_length(
        self,
        sentence,
        language,
        native_language
    ):
        """
        Property test: Difficulty is calculated based on sentence length.
        
        For ANY valid sentence:
        1. Generate explanation
        2. Verify difficulty matches expected value based on word count:
           - < 8 words: 'beginner'
           - 8-14 words: 'intermediate'
           - >= 15 words: 'advanced'
        
        This validates the difficulty calculation logic.
        
        **Validates: Requirement 5.5**
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock successful generation
            assistant.study_manager.generate_sentence_explanation = Mock(
                return_value=(True, "**Translation:**\nA translation", {'grammar': []})
            )
            
            # Get explanation
            result = assistant.get_sentence_explanation(
                sentence=sentence,
                paragraph_context="",
                language=language,
                native_language=native_language
            )
            
            # Calculate expected difficulty based on word count
            word_count = len(sentence.split())
            if word_count < 8:
                expected_difficulty = 'beginner'
            elif word_count < 15:
                expected_difficulty = 'intermediate'
            else:
                expected_difficulty = 'advanced'
            
            # Verify difficulty matches expected value
            assert result['difficulty'] == expected_difficulty, \
                f"For {word_count} words, expected difficulty '{expected_difficulty}', got '{result['difficulty']}'"
            
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
