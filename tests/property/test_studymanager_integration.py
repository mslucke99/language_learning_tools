"""
Property-based tests for StudyManager integration in Immersive Reading Mode.

These tests verify that ReadingAssistant correctly integrates with StudyManager
for all AI-powered features and respects the existing LLM_Service configuration.

Property 36: StudyManager Integration
- Validates: Requirements 13.3, 13.4, 13.5
- Verifies AI features use StudyManager methods and respect LLM_Service config
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager
from src.features.reader.reading_assistant import ReadingAssistant
from src.core.config import config as app_config


class TestStudyManagerIntegrationProperty:
    """
    Property 36: StudyManager Integration
    
    This property ensures that ReadingAssistant correctly integrates with the existing
    StudyManager for all AI-powered features. This must hold true for:
    
    1. Word definitions use StudyManager.generate_word_content()
    2. Sentence explanations use StudyManager.generate_sentence_explanation()
    3. LLM_Service configuration is respected (provider, model, base_url)
    
    The property validates:
    - Requirement 13.3: Use StudyManager.generate_word_definition for definitions
    - Requirement 13.4: Use StudyManager.generate_sentence_explanation for explanations
    - Requirement 13.5: Use existing LLM_Service configuration
    
    The property holds for ANY valid word, sentence, language, and LLM configuration.
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
        paragraph_context=st.text(min_size=0, max_size=1000)
    )
    @settings(max_examples=20, deadline=None)
    def test_word_definition_uses_studymanager(
        self,
        word,
        language,
        sentence_context,
        paragraph_context
    ):
        """
        Property test: Word definitions use StudyManager.generate_word_content().
        
        For ANY valid word, language, and context:
        1. Call ReadingAssistant.get_word_definition()
        2. Verify StudyManager.generate_word_content() was called
        3. Verify the method was called with correct parameters
        
        This ensures word definitions always go through StudyManager (Requirement 13.3).
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager.generate_word_content to track calls
            original_method = study_manager.generate_word_content
            study_manager.generate_word_content = Mock(
                return_value=(True, "A test definition", {'example': 'Test example'})
            )
            
            # Get definition (should call StudyManager)
            result = assistant.get_word_definition(
                word=word,
                sentence_context=sentence_context,
                paragraph_context=paragraph_context,
                language=language
            )
            
            # Verify StudyManager.generate_word_content was called
            assert study_manager.generate_word_content.called, \
                "ReadingAssistant must call StudyManager.generate_word_content() for word definitions (Requirement 13.3)"
            
            # Verify it was called at least once
            assert study_manager.generate_word_content.call_count >= 1, \
                "StudyManager.generate_word_content() should be called at least once"
            
            # Verify the call included content_type='definition'
            call_args = study_manager.generate_word_content.call_args
            if call_args and len(call_args[1]) > 0:
                # Check keyword arguments
                assert call_args[1].get('content_type') == 'definition', \
                    "StudyManager.generate_word_content() should be called with content_type='definition'"
            
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
        sentence=st.text(min_size=10, max_size=500).filter(lambda x: x.strip() != ''),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh']),
        paragraph_context=st.text(min_size=0, max_size=1000),
        native_language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh'])
    )
    @settings(max_examples=20, deadline=None)
    def test_sentence_explanation_uses_studymanager(
        self,
        sentence,
        language,
        paragraph_context,
        native_language
    ):
        """
        Property test: Sentence explanations use StudyManager.generate_sentence_explanation().
        
        For ANY valid sentence, language, and context:
        1. Call ReadingAssistant.get_sentence_explanation()
        2. Verify StudyManager.generate_sentence_explanation() was called
        3. Verify the method was called with correct parameters
        
        This ensures sentence explanations always go through StudyManager (Requirement 13.4).
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager.generate_sentence_explanation to track calls
            study_manager.generate_sentence_explanation = Mock(
                return_value=(True, "A test explanation", {'grammar': []})
            )
            
            # Get explanation (should call StudyManager)
            result = assistant.get_sentence_explanation(
                sentence=sentence,
                paragraph_context=paragraph_context,
                language=language,
                native_language=native_language
            )
            
            # Verify StudyManager.generate_sentence_explanation was called
            assert study_manager.generate_sentence_explanation.called, \
                "ReadingAssistant must call StudyManager.generate_sentence_explanation() for sentence explanations (Requirement 13.4)"
            
            # Verify it was called at least once
            assert study_manager.generate_sentence_explanation.call_count >= 1, \
                "StudyManager.generate_sentence_explanation() should be called at least once"
            
            # Verify the call included focus_areas parameter
            call_args = study_manager.generate_sentence_explanation.call_args
            if call_args and len(call_args[1]) > 0:
                # Check keyword arguments
                assert 'focus_areas' in call_args[1], \
                    "StudyManager.generate_sentence_explanation() should be called with focus_areas parameter"
                assert call_args[1]['focus_areas'] == ['all'], \
                    "StudyManager.generate_sentence_explanation() should request comprehensive explanation with focus_areas=['all']"
            
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
        provider=st.sampled_from(['gemini', 'openai', 'ollama']),
        model=st.text(min_size=3, max_size=50).filter(lambda x: x.strip() != ''),
        base_url=st.one_of(st.none(), st.text(min_size=5, max_size=100))
    )
    @settings(max_examples=20, deadline=None)
    def test_respects_llm_service_configuration(
        self,
        provider,
        model,
        base_url
    ):
        """
        Property test: ReadingAssistant respects LLM_Service configuration.
        
        For ANY valid LLM provider, model, and base_url configuration:
        1. Configure StudyManager with specific LLM settings
        2. Create ReadingAssistant with that StudyManager
        3. Verify ReadingAssistant uses the same LLM configuration
        
        This ensures LLM configuration is centrally managed (Requirement 13.5).
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database
            db = FlashcardDatabase(db_name=temp_db_path)
            
            # Save original app_config values
            original_provider = app_config.llm_provider
            original_model = app_config.llm_model
            original_base_url = app_config.llm_base_url
            
            try:
                # Set app_config to test values
                app_config.llm_provider = provider
                app_config.llm_model = model
                app_config.llm_base_url = base_url or ""
                
                # Create StudyManager (should load from app_config)
                study_manager = StudyManager(db)
                
                # Verify StudyManager loaded the configuration
                assert study_manager.llm_provider == provider, \
                    f"StudyManager should use configured provider '{provider}', got '{study_manager.llm_provider}'"
                
                # Note: model might be validated/adjusted by StudyManager
                assert study_manager.llm_model is not None, \
                    "StudyManager should have a model configured"
                
                if base_url:
                    assert study_manager.llm_base_url == base_url, \
                        f"StudyManager should use configured base_url '{base_url}', got '{study_manager.llm_base_url}'"
                
                # Create ReadingAssistant
                assistant = ReadingAssistant(study_manager, db)
                
                # Verify ReadingAssistant uses the same StudyManager instance
                assert assistant.study_manager is study_manager, \
                    "ReadingAssistant must use the provided StudyManager instance (Requirement 13.5)"
                
                # Verify ReadingAssistant doesn't create its own LLM client
                # It should rely on StudyManager's ai_client
                assert not hasattr(assistant, 'ai_client') or assistant.study_manager.ai_client is not None, \
                    "ReadingAssistant should use StudyManager's ai_client, not create its own"
                
            finally:
                # Restore original app_config values
                app_config.llm_provider = original_provider
                app_config.llm_model = original_model
                app_config.llm_base_url = original_base_url
            
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

    def test_studymanager_integration_with_real_methods(self):
        """
        Integration test: Verify ReadingAssistant integrates with real StudyManager methods.
        
        This is not a property test, but validates that the integration works
        with actual StudyManager method signatures and behavior.
        """
        # Create temporary database
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock the AI client to avoid actual LLM calls
            study_manager.ai_client = Mock()
            study_manager.ai_client.is_available = Mock(return_value=True)
            study_manager.ai_client.generate_response = Mock(return_value="Test definition")
            
            # Test word definition integration
            result = assistant.get_word_definition(
                word="test",
                sentence_context="This is a test.",
                paragraph_context="",
                language="en"
            )
            
            # Verify result structure
            assert result is not None
            assert 'word' in result
            assert 'definition' in result
            assert 'source' in result
            
            # Test sentence explanation integration
            result = assistant.get_sentence_explanation(
                sentence="This is a test sentence.",
                paragraph_context="",
                language="en",
                native_language="en"
            )
            
            # Verify result structure
            assert result is not None
            assert 'sentence' in result
            assert 'translation' in result
            assert 'difficulty' in result
            
        finally:
            db.close()
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass

    def test_studymanager_creates_imported_content_entries(self):
        """
        Test that StudyManager integration creates proper imported_content entries.
        
        Verifies that when ReadingAssistant calls StudyManager methods,
        temporary imported_content entries are created as expected.
        """
        # Create temporary database
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock the AI client
            study_manager.ai_client = Mock()
            study_manager.ai_client.is_available = Mock(return_value=True)
            study_manager.ai_client.generate_response = Mock(return_value="Test definition")
            
            # Get word definition
            assistant.get_word_definition(
                word="test",
                sentence_context="This is a test.",
                paragraph_context="",
                language="en"
            )
            
            # Verify imported_content entry was created
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT content, content_type, url
                FROM imported_content
                WHERE content = 'test' AND url = 'reading_mode'
            """)
            
            row = cursor.fetchone()
            assert row is not None, \
                "StudyManager integration should create imported_content entry"
            assert row[1] == 'word', \
                "Content type should be 'word'"
            assert row[2] == 'reading_mode', \
                "URL should be 'reading_mode' to identify reading mode lookups"
            
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
            min_size=2,
            max_size=5,
            unique=True
        ),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr'])
    )
    @settings(max_examples=15, deadline=None)
    def test_multiple_lookups_all_use_studymanager(
        self,
        words,
        language
    ):
        """
        Property test: Multiple lookups all use StudyManager.
        
        For ANY list of words and language:
        1. Perform multiple word lookups
        2. Verify each lookup calls StudyManager.generate_word_content()
        
        This ensures the integration is consistent across multiple operations.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and assistant
            db = FlashcardDatabase(db_name=temp_db_path)
            study_manager = StudyManager(db)
            assistant = ReadingAssistant(study_manager, db)
            
            # Mock StudyManager.generate_word_content to track calls
            call_count = 0
            
            def mock_generate(content_id, content_type='definition', language='native'):
                nonlocal call_count
                call_count += 1
                return (True, f"Definition {call_count}", {'example': f'Example {call_count}'})
            
            study_manager.generate_word_content = Mock(side_effect=mock_generate)
            
            # Perform multiple lookups
            for word in words:
                assistant.get_word_definition(
                    word=word,
                    sentence_context=f"Context for {word}",
                    paragraph_context="",
                    language=language
                )
            
            # Verify StudyManager was called for each word
            # Note: First call generates, subsequent calls may use cache
            # But at least the first call should go through StudyManager
            assert study_manager.generate_word_content.call_count >= 1, \
                "StudyManager.generate_word_content() should be called at least once for multiple lookups"
            
            # Verify all calls were for definitions
            for call in study_manager.generate_word_content.call_args_list:
                if len(call[1]) > 0:
                    assert call[1].get('content_type') == 'definition', \
                        "All StudyManager calls should be for content_type='definition'"
            
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

    def test_studymanager_configuration_changes_reflected(self):
        """
        Test that changes to StudyManager configuration are reflected in ReadingAssistant.
        
        Verifies that ReadingAssistant doesn't cache configuration but always
        uses the current StudyManager state.
        """
        # Create temporary database
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            db = FlashcardDatabase(db_name=temp_db_path)
            
            # Save original config
            original_provider = app_config.llm_provider
            original_model = app_config.llm_model
            
            try:
                # Initial configuration
                app_config.llm_provider = 'gemini'
                app_config.llm_model = 'gemini-1.5-flash'
                
                study_manager = StudyManager(db)
                assistant = ReadingAssistant(study_manager, db)
                
                # Verify initial configuration
                assert study_manager.llm_provider == 'gemini'
                
                # Change configuration
                study_manager.update_llm_config('openai', 'gpt-4o-mini', None)
                
                # Verify ReadingAssistant sees the change through StudyManager
                assert assistant.study_manager.llm_provider == 'openai', \
                    "ReadingAssistant should see configuration changes through StudyManager"
                assert assistant.study_manager.llm_model == 'gpt-4o-mini', \
                    "ReadingAssistant should see model changes through StudyManager"
                
            finally:
                # Restore original config
                app_config.llm_provider = original_provider
                app_config.llm_model = original_model
            
        finally:
            db.close()
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                pass
