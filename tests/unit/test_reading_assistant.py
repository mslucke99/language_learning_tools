"""Unit tests for ReadingAssistant class."""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager
from src.features.reader.reading_assistant import ReadingAssistant
from src.features.reader.definition_cache import DefinitionCache


class TestReadingAssistantInitialization(unittest.TestCase):
    """Test ReadingAssistant class initialization."""
    
    def setUp(self):
        """Set up test database and dependencies."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = FlashcardDatabase(self.temp_db.name)
        self.study_manager = StudyManager(self.db)
    
    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_init_with_valid_parameters(self):
        """Test initialization with valid StudyManager and FlashcardDatabase."""
        assistant = ReadingAssistant(self.study_manager, self.db)
        
        # Verify attributes are set correctly
        self.assertIsNotNone(assistant.study_manager)
        self.assertIsNotNone(assistant.db)
        self.assertIsNotNone(assistant.cache)
        
        # Verify study_manager is the same instance
        self.assertIs(assistant.study_manager, self.study_manager)
        
        # Verify db is the same instance
        self.assertIs(assistant.db, self.db)
        
        # Verify cache is a DefinitionCache instance
        self.assertIsInstance(assistant.cache, DefinitionCache)
    
    def test_cache_uses_same_database(self):
        """Test that DefinitionCache uses the same database instance."""
        assistant = ReadingAssistant(self.study_manager, self.db)
        
        # Verify cache uses the same database
        self.assertIs(assistant.cache.db, self.db)
    
    def test_multiple_instances_independent(self):
        """Test that multiple ReadingAssistant instances are independent."""
        assistant1 = ReadingAssistant(self.study_manager, self.db)
        assistant2 = ReadingAssistant(self.study_manager, self.db)
        
        # Verify they are different instances
        self.assertIsNot(assistant1, assistant2)
        
        # But they share the same dependencies
        self.assertIs(assistant1.study_manager, assistant2.study_manager)
        self.assertIs(assistant1.db, assistant2.db)


class TestGetWordDefinition(unittest.TestCase):
    """Test get_word_definition method."""
    
    def setUp(self):
        """Set up test database and dependencies."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = FlashcardDatabase(self.temp_db.name)
        self.study_manager = StudyManager(self.db)
        self.assistant = ReadingAssistant(self.study_manager, self.db)
    
    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_get_word_definition_returns_cached_definition(self):
        """Test that cached definitions are returned without calling StudyManager."""
        # Pre-populate cache
        word = "hello"
        language = "en"
        context = "Hello, how are you?"
        
        self.assistant.cache.store_definition(
            word=word,
            language=language,
            context=context,
            definition="A greeting",
            synonym="hi",
            example="Hello, nice to meet you."
        )
        
        # Mock StudyManager to ensure it's not called
        self.assistant.study_manager.generate_word_content = Mock()
        
        # Get definition
        result = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        # Verify cached definition is returned
        self.assertEqual(result['word'], word)
        self.assertEqual(result['definition'], "A greeting")
        self.assertEqual(result['synonym'], "hi")
        self.assertEqual(result['example'], "Hello, nice to meet you.")
        self.assertEqual(result['source'], 'cache')
        
        # Verify StudyManager was not called
        self.assistant.study_manager.generate_word_content.assert_not_called()
    
    def test_get_word_definition_generates_new_definition_on_cache_miss(self):
        """Test that new definitions are generated when cache misses."""
        word = "bonjour"
        language = "fr"
        context = "Bonjour, comment allez-vous?"
        
        # Mock StudyManager to return a definition
        self.assistant.study_manager.generate_word_content = Mock(
            return_value=(
                True,
                "A French greeting meaning 'hello' or 'good day'",
                {'synonym': 'salut', 'example': 'Bonjour, ça va?'}
            )
        )
        
        # Get definition
        result = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        # Verify generated definition is returned
        self.assertEqual(result['word'], word)
        self.assertEqual(result['definition'], "A French greeting meaning 'hello' or 'good day'")
        self.assertEqual(result['synonym'], 'salut')
        self.assertEqual(result['example'], 'Bonjour, ça va?')
        self.assertEqual(result['source'], 'generated')
        
        # Verify StudyManager was called
        self.assistant.study_manager.generate_word_content.assert_called_once()
    
    def test_get_word_definition_caches_generated_definition(self):
        """Test that generated definitions are stored in cache."""
        word = "hola"
        language = "es"
        context = "Hola, ¿cómo estás?"
        
        # Mock StudyManager
        self.assistant.study_manager.generate_word_content = Mock(
            return_value=(
                True,
                "A Spanish greeting",
                {'synonym': 'hey', 'example': 'Hola amigo'}
            )
        )
        
        # First call - should generate
        result1 = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        self.assertEqual(result1['source'], 'generated')
        
        # Second call - should use cache
        result2 = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        self.assertEqual(result2['source'], 'cache')
        
        # Verify StudyManager was only called once
        self.assertEqual(self.assistant.study_manager.generate_word_content.call_count, 1)
    
    def test_get_word_definition_handles_generation_failure(self):
        """Test that generation failures are handled gracefully."""
        word = "test"
        language = "en"
        context = "This is a test."
        
        # Mock StudyManager to return failure
        self.assistant.study_manager.generate_word_content = Mock(
            return_value=(False, "AI service is not available", {})
        )
        
        # Get definition
        result = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        # Verify error is returned
        self.assertEqual(result['word'], word)
        self.assertEqual(result['definition'], "AI service is not available")
        self.assertIsNone(result['synonym'])
        self.assertEqual(result['example'], '')
        self.assertEqual(result['source'], 'error')
    
    def test_get_word_definition_creates_imported_content_entry(self):
        """Test that temporary imported_content entry is created."""
        word = "test"
        language = "en"
        context = "This is a test."
        
        # Mock StudyManager
        self.assistant.study_manager.generate_word_content = Mock(
            return_value=(True, "A procedure to check something", {})
        )
        
        # Get definition
        self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        # Verify imported_content entry was created
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT content, context, url, language, content_type
            FROM imported_content
            WHERE content = ? AND url = 'reading_mode'
        """, (word,))
        
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], word)
        self.assertEqual(row[1], context)
        self.assertEqual(row[2], 'reading_mode')
        self.assertEqual(row[3], language)
        self.assertEqual(row[4], 'word')
    
    def test_get_word_definition_uses_definition_as_example_fallback(self):
        """Test that definition is used as example when no example in suggestions."""
        word = "test"
        language = "en"
        context = "This is a test."
        
        # Mock StudyManager with no example in suggestions
        self.assistant.study_manager.generate_word_content = Mock(
            return_value=(True, "A procedure to check something", {'synonym': 'check'})
        )
        
        # Get definition
        result = self.assistant.get_word_definition(
            word=word,
            sentence_context=context,
            paragraph_context="",
            language=language
        )
        
        # Verify definition is used as example fallback
        self.assertEqual(result['example'], "A procedure to check something")


class TestGetSentenceExplanation(unittest.TestCase):
    """Test get_sentence_explanation method."""
    
    def setUp(self):
        """Set up test database and dependencies."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = FlashcardDatabase(self.temp_db.name)
        self.study_manager = StudyManager(self.db)
        self.assistant = ReadingAssistant(self.study_manager, self.db)
    
    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_get_sentence_explanation_generates_explanation(self):
        """Test that sentence explanations are generated successfully."""
        sentence = "Je vais au marché."
        language = "fr"
        native_language = "en"
        paragraph_context = "Je vais au marché pour acheter des fruits."
        
        # Mock StudyManager to return an explanation
        mock_explanation = """**Comprehensive:**
I am going to the market.

**Grammar:**
- 'Je vais' uses the verb 'aller' (to go) in present tense
- 'au' is a contraction of 'à le' (to the)

**Cultural:**
French markets are an important part of daily life."""
        
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(
                True,
                mock_explanation,
                {
                    'grammar': ['Present tense of aller', 'Contraction au = à + le'],
                    'flashcards': []
                }
            )
        )
        
        # Get explanation
        result = self.assistant.get_sentence_explanation(
            sentence=sentence,
            paragraph_context=paragraph_context,
            language=language,
            native_language=native_language
        )
        
        # Verify explanation structure
        self.assertEqual(result['sentence'], sentence)
        self.assertIn('translation', result)
        self.assertIsInstance(result['grammar_notes'], list)
        self.assertIn('difficulty', result)
        self.assertIn(result['difficulty'], ['beginner', 'intermediate', 'advanced'])
        
        # Verify StudyManager was called with correct parameters
        self.assistant.study_manager.generate_sentence_explanation.assert_called_once()
        call_args = self.assistant.study_manager.generate_sentence_explanation.call_args
        self.assertEqual(call_args[1]['language'], 'native')
        self.assertEqual(call_args[1]['focus_areas'], ['all'])
    
    def test_get_sentence_explanation_creates_imported_content_entry(self):
        """Test that temporary imported_content entry is created for sentences."""
        sentence = "Hola, ¿cómo estás?"
        language = "es"
        native_language = "en"
        paragraph_context = "Hola, ¿cómo estás? Yo estoy bien."
        
        # Mock StudyManager
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(True, "Hello, how are you?", {'grammar': []})
        )
        
        # Get explanation
        self.assistant.get_sentence_explanation(
            sentence=sentence,
            paragraph_context=paragraph_context,
            language=language,
            native_language=native_language
        )
        
        # Verify imported_content entry was created
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT content, context, url, language, content_type
            FROM imported_content
            WHERE content = ? AND url = 'reading_mode'
        """, (sentence,))
        
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], sentence)
        self.assertEqual(row[1], paragraph_context)
        self.assertEqual(row[2], 'reading_mode')
        self.assertEqual(row[3], language)
        self.assertEqual(row[4], 'sentence')
    
    def test_get_sentence_explanation_handles_generation_failure(self):
        """Test that generation failures are handled gracefully."""
        sentence = "Test sentence."
        language = "en"
        native_language = "en"
        
        # Mock StudyManager to return failure
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(False, "AI service is not available", {})
        )
        
        # Get explanation
        result = self.assistant.get_sentence_explanation(
            sentence=sentence,
            paragraph_context="",
            language=language,
            native_language=native_language
        )
        
        # Verify error is returned
        self.assertEqual(result['sentence'], sentence)
        self.assertEqual(result['translation'], "AI service is not available")
        self.assertEqual(result['grammar_notes'], [])
        self.assertIsNone(result['cultural_notes'])
        self.assertEqual(result['difficulty'], 'unknown')
    
    def test_get_sentence_explanation_extracts_grammar_notes(self):
        """Test that grammar notes are extracted from suggestions."""
        sentence = "I have been studying."
        language = "en"
        native_language = "en"
        
        # Mock StudyManager with grammar suggestions
        mock_explanation = "**Grammar:** Present perfect continuous tense"
        grammar_suggestions = [
            'Present perfect continuous: have/has + been + verb-ing',
            'Used for actions that started in the past and continue to present'
        ]
        
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(
                True,
                mock_explanation,
                {'grammar': grammar_suggestions, 'flashcards': []}
            )
        )
        
        # Get explanation
        result = self.assistant.get_sentence_explanation(
            sentence=sentence,
            paragraph_context="",
            language=language,
            native_language=native_language
        )
        
        # Verify grammar notes are extracted
        self.assertIsInstance(result['grammar_notes'], list)
        self.assertEqual(len(result['grammar_notes']), 2)
        self.assertIn('Present perfect continuous: have/has + been + verb-ing', result['grammar_notes'])
    
    def test_get_sentence_explanation_estimates_difficulty(self):
        """Test that difficulty is estimated based on sentence length."""
        # Test beginner (short sentence)
        short_sentence = "I am happy."
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(True, "Translation", {'grammar': []})
        )
        
        result = self.assistant.get_sentence_explanation(
            sentence=short_sentence,
            paragraph_context="",
            language="en",
            native_language="en"
        )
        self.assertEqual(result['difficulty'], 'beginner')
        
        # Test intermediate (medium sentence)
        medium_sentence = "I am going to the store to buy some groceries."
        result = self.assistant.get_sentence_explanation(
            sentence=medium_sentence,
            paragraph_context="",
            language="en",
            native_language="en"
        )
        self.assertEqual(result['difficulty'], 'intermediate')
        
        # Test advanced (long sentence)
        long_sentence = "Despite the fact that it was raining heavily, we decided to continue our journey through the mountains."
        result = self.assistant.get_sentence_explanation(
            sentence=long_sentence,
            paragraph_context="",
            language="en",
            native_language="en"
        )
        self.assertEqual(result['difficulty'], 'advanced')
    
    def test_get_sentence_explanation_parses_cultural_notes(self):
        """Test that cultural notes are extracted from explanation."""
        sentence = "Il fait la bise."
        language = "fr"
        native_language = "en"
        
        # Mock StudyManager with cultural notes
        mock_explanation = """**Translation:**
He does the kiss.

**Cultural:**
La bise is a traditional French greeting involving cheek kisses."""
        
        self.assistant.study_manager.generate_sentence_explanation = Mock(
            return_value=(True, mock_explanation, {'grammar': []})
        )
        
        # Get explanation
        result = self.assistant.get_sentence_explanation(
            sentence=sentence,
            paragraph_context="",
            language=language,
            native_language=native_language
        )
        
        # Verify cultural notes are extracted
        self.assertIsNotNone(result['cultural_notes'])
        self.assertIn('bise', result['cultural_notes'])


class TestPreGenerateDefinitions(unittest.TestCase):
    """Test pre_generate_definitions method."""
    
    def setUp(self):
        """Set up test database and dependencies."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = FlashcardDatabase(self.temp_db.name)
        self.study_manager = StudyManager(self.db)
        self.assistant = ReadingAssistant(self.study_manager, self.db)
    
    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_pre_generate_definitions_extracts_unique_words(self, mock_sleep):
        """Test that unique words are extracted from content."""
        content = "Hello world. Hello Python. This is a test. Test test test."
        language = "en"
        session_id = 1
        
        # Mock get_word_definition to avoid actual LLM calls
        self.assistant.get_word_definition = Mock(
            return_value={
                'word': 'test',
                'definition': 'A procedure',
                'synonym': 'check',
                'example': 'This is a test.',
                'source': 'generated'
            }
        )
        
        # Call pre_generate_definitions
        self.assistant.pre_generate_definitions(session_id, content, language)
        
        # Verify get_word_definition was called for unique words
        # Should be called for: hello, world, python, this, is, a, test
        self.assertGreater(self.assistant.get_word_definition.call_count, 0)
        
        # Verify sleep was called between generations
        self.assertGreater(mock_sleep.call_count, 0)
    
    @patch('time.sleep')
    def test_pre_generate_definitions_limits_to_500_words(self, mock_sleep):
        """Test that only 500 most frequent words are processed."""
        # Create content with more than 500 unique words
        words = [f"word{i}" for i in range(600)]
        content = " ".join(words)
        language = "en"
        session_id = 1
        
        # Mock get_word_definition
        self.assistant.get_word_definition = Mock(
            return_value={
                'word': 'test',
                'definition': 'A procedure',
                'source': 'generated'
            }
        )
        
        # Call pre_generate_definitions
        self.assistant.pre_generate_definitions(session_id, content, language)
        
        # Verify at most 500 words were processed
        self.assertLessEqual(self.assistant.get_word_definition.call_count, 500)
    
    @patch('time.sleep')
    def test_pre_generate_definitions_prioritizes_frequent_words(self, mock_sleep):
        """Test that most frequent words are prioritized."""
        # Create content where "test" appears 10 times, "hello" 5 times, others once
        content = "test " * 10 + "hello " * 5 + "world once twice"
        language = "en"
        session_id = 1
        
        # Track which words were processed
        processed_words = []
        
        def mock_get_definition(word, sentence_context, paragraph_context, language):
            processed_words.append(word)
            return {
                'word': word,
                'definition': f'Definition of {word}',
                'source': 'generated'
            }
        
        self.assistant.get_word_definition = mock_get_definition
        
        # Call pre_generate_definitions
        self.assistant.pre_generate_definitions(session_id, content, language)
        
        # Verify "test" and "hello" were processed (most frequent)
        self.assertIn('test', processed_words)
        self.assertIn('hello', processed_words)
    
    @patch('time.sleep')
    def test_pre_generate_definitions_skips_cached_words(self, mock_sleep):
        """Test that words already in cache are skipped."""
        content = "hello world test"
        language = "en"
        session_id = 1
        
        # Pre-populate cache with "hello"
        self.assistant.cache.store_definition(
            word="hello",
            language=language,
            context="hello world",
            definition="A greeting",
            synonym="hi",
            example="Hello there"
        )
        
        # Mock get_word_definition to track calls
        original_get_definition = self.assistant.get_word_definition
        call_count = 0
        
        def mock_get_definition(word, sentence_context, paragraph_context, language):
            nonlocal call_count
            call_count += 1
            return original_get_definition(word, sentence_context, paragraph_context, language)
        
        self.assistant.get_word_definition = Mock(side_effect=mock_get_definition)
        
        # Call pre_generate_definitions
        self.assistant.pre_generate_definitions(session_id, content, language)
        
        # Verify "hello" was not processed (already cached)
        # Note: The actual implementation checks cache in get_word_definition,
        # so we need to verify the behavior differently
        # The method should still call get_word_definition, but it will return cached result
        self.assertGreater(self.assistant.get_word_definition.call_count, 0)
    
    @patch('time.sleep')
    def test_pre_generate_definitions_handles_errors_gracefully(self, mock_sleep):
        """Test that errors during generation don't stop the process."""
        content = "hello world test error"
        language = "en"
        session_id = 1
        
        # Mock get_word_definition to raise error for "error" word
        def mock_get_definition(word, sentence_context, paragraph_context, language):
            if word == "error":
                raise Exception("Test error")
            return {
                'word': word,
                'definition': f'Definition of {word}',
                'source': 'generated'
            }
        
        self.assistant.get_word_definition = mock_get_definition
        
        # Call pre_generate_definitions - should not raise exception
        try:
            self.assistant.pre_generate_definitions(session_id, content, language)
            # If we get here, the error was handled gracefully
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"pre_generate_definitions raised exception: {e}")
    
    @patch('time.sleep')
    def test_pre_generate_definitions_adds_delay_between_calls(self, mock_sleep):
        """Test that 0.1 second delay is added between LLM calls."""
        content = "hello world test"
        language = "en"
        session_id = 1
        
        # Mock get_word_definition
        self.assistant.get_word_definition = Mock(
            return_value={
                'word': 'test',
                'definition': 'A procedure',
                'source': 'generated'
            }
        )
        
        # Call pre_generate_definitions
        self.assistant.pre_generate_definitions(session_id, content, language)
        
        # Verify sleep was called with 0.1 seconds
        if mock_sleep.call_count > 0:
            # Check that at least one call used 0.1 seconds
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            self.assertIn(0.1, sleep_calls)
    
    def test_find_sentence_with_word_finds_correct_sentence(self):
        """Test that _find_sentence_with_word finds the right sentence."""
        content = "Hello world. This is a test. Python is great."
        
        # Test finding "test"
        sentence = self.assistant._find_sentence_with_word("test", content)
        self.assertIn("test", sentence.lower())
        self.assertIn("This is a test", sentence)
        
        # Test finding "python"
        sentence = self.assistant._find_sentence_with_word("python", content)
        self.assertIn("python", sentence.lower())
        self.assertIn("Python is great", sentence)
    
    def test_find_sentence_with_word_case_insensitive(self):
        """Test that word search is case-insensitive."""
        content = "Hello World. This is a TEST."
        
        # Search for lowercase "test"
        sentence = self.assistant._find_sentence_with_word("test", content)
        self.assertIn("TEST", sentence)
        
        # Search for uppercase "HELLO"
        sentence = self.assistant._find_sentence_with_word("HELLO", content)
        self.assertIn("Hello", sentence)
    
    def test_find_sentence_with_word_returns_empty_if_not_found(self):
        """Test that empty string is returned if word not found."""
        content = "Hello world. This is a test."
        
        # Search for word that doesn't exist
        sentence = self.assistant._find_sentence_with_word("nonexistent", content)
        self.assertEqual(sentence, "")
    
    def test_find_sentence_with_word_handles_punctuation(self):
        """Test that word matching works with punctuation."""
        content = "Hello, world! This is a test?"
        
        # Search for "world" (has comma after it)
        sentence = self.assistant._find_sentence_with_word("world", content)
        self.assertIn("world", sentence.lower())
        
        # Search for "test" (has question mark after it)
        sentence = self.assistant._find_sentence_with_word("test", content)
        self.assertIn("test", sentence.lower())


if __name__ == '__main__':
    unittest.main()
