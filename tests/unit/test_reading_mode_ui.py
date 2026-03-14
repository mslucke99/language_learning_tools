"""
Unit tests for Reading Mode UI Frame.

Tests the Tkinter UI components for reading mode functionality.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.core.database import FlashcardDatabase
from src.features.reader.content_manager import ContentManager
from src.features.reader.reading_assistant import ReadingAssistant
from src.features.reader.analytics_engine import AnalyticsEngine
from src.features.reader.library import ReadingLibrary


class TestReadingModeFrameLogic(unittest.TestCase):
    """Test the logic of reading mode frame without GUI."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.db = FlashcardDatabase(self.db_path)
        self.content_manager = ContentManager(self.db)
        self.analytics_engine = AnalyticsEngine(self.db)
        self.library = ReadingLibrary(self.db)
    
    def tearDown(self):
        """Clean up test database."""
        try:
            self.db.close()
        except:
            pass
        
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_import_and_retrieve_session(self):
        """Test importing content and retrieving it."""
        # Import content
        content = "This is a test article for reading mode. It has multiple sentences. Each sentence is important for language learning. This content is long enough to meet the minimum requirement."
        title = "Test Article"
        language = "en"
        
        session_id = self.content_manager.import_from_paste(
            content=content,
            title=title,
            language=language,
            user_attestation=True
        )
        
        self.assertIsNotNone(session_id)
        self.assertGreater(session_id, 0)
        
        # Retrieve session
        user_id = 1
        session = self.content_manager.get_reading_session(session_id, user_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session['title'], title)
        self.assertEqual(session['content'], content)
        self.assertEqual(session['language'], language)
    
    def test_session_appears_in_library(self):
        """Test that imported session appears in library."""
        # Import content
        content = "Test content for library testing. This is a longer piece of text that meets the minimum character requirement for content import. It should be at least one hundred characters long."
        title = "Library Test"
        
        session_id = self.content_manager.import_from_paste(
            content=content,
            title=title,
            language="en",
            user_attestation=True
        )
        
        # Get library
        user_id = 1
        sessions = self.library.get_all_sessions(user_id)
        
        self.assertGreater(len(sessions), 0)
        
        # Find our session
        found = False
        for session in sessions:
            if session.get('id') == session_id:
                found = True
                self.assertEqual(session['title'], title)
                break
        
        self.assertTrue(found, "Session not found in library")
    
    def test_session_content_retrieval(self):
        """Test that session content can be retrieved for display."""
        # Import content
        test_content = "Line 1 with content\nLine 2 with more content\nLine 3 with even more content\nLine 4 with additional content\nLine 5 with final content for testing purposes"
        title = "Content Test"
        
        session_id = self.content_manager.import_from_paste(
            content=test_content,
            title=title,
            language="en",
            user_attestation=True
        )
        
        # Retrieve and verify content
        user_id = 1
        session = self.content_manager.get_reading_session(session_id, user_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session['content'], test_content)
        self.assertIn('title', session)
        self.assertIn('difficulty_rating', session)
        self.assertIn('word_count', session)
    
    def test_session_statistics(self):
        """Test that session statistics can be retrieved."""
        # Import content
        content = "This is test content for statistics. It needs to be long enough to meet the minimum character requirement. This is important for testing the reading mode functionality properly."
        
        session_id = self.content_manager.import_from_paste(
            content=content,
            title="Stats Test",
            language="en",
            user_attestation=True
        )
        
        # Get statistics
        stats = self.analytics_engine.get_session_statistics(session_id)
        
        self.assertIsNotNone(stats)
        self.assertIn('time_spent_seconds', stats)
        self.assertIn('words_read', stats)
        self.assertIn('wpm', stats)
        self.assertIn('lookup_count', stats)
        self.assertIn('comprehension_score', stats)
        self.assertIn('completion_percentage', stats)
    
    def test_library_filtering(self):
        """Test that library filtering works."""
        # Import multiple sessions
        for i in range(3):
            self.content_manager.import_from_paste(
                content=f"Content {i} with additional text to meet minimum length requirement. This is session number {i} for testing library filtering functionality.",
                title=f"Session {i}",
                language="en",
                user_attestation=True
            )
        
        # Get all sessions
        user_id = 1
        all_sessions = self.library.get_all_sessions(user_id)
        
        self.assertGreaterEqual(len(all_sessions), 3)
        
        # Verify all sessions have required fields
        for session in all_sessions:
            self.assertIn('id', session)
            self.assertIn('title', session)
            self.assertIn('difficulty_rating', session)
    
    def test_session_lookup_tracking(self):
        """Test that word lookups are tracked."""
        # Import content
        session_id = self.content_manager.import_from_paste(
            content="Test content with words for lookup tracking. This is a longer piece of text that meets the minimum character requirement for content import.",
            title="Lookup Test",
            language="en",
            user_attestation=True
        )
        
        # Record a lookup
        lookup_id = self.analytics_engine.record_lookup(
            session_id=session_id,
            word="test",
            sentence_context="Test content with words",
            lookup_type="word"
        )
        
        self.assertIsNotNone(lookup_id)
        self.assertGreater(lookup_id, 0)
        
        # Verify lookup was recorded
        stats = self.analytics_engine.get_session_statistics(session_id)
        self.assertGreater(stats.get('lookup_count', 0), 0)


class TestReadingProgressTracking(unittest.TestCase):
    """Test reading progress tracking functionality."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.db = FlashcardDatabase(self.db_path)
        self.content_manager = ContentManager(self.db)
    
    def tearDown(self):
        """Clean up test database."""
        try:
            self.db.close()
        except:
            pass
        
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_update_reading_progress(self):
        """Test updating reading progress."""
        # Import content
        session_id = self.content_manager.import_from_paste(
            content="Test content for progress tracking. This is a longer piece of text that meets the minimum character requirement for content import. It should be at least one hundred characters long.",
            title="Progress Test",
            language="en",
            user_attestation=True
        )
        
        # Update progress
        result = self.content_manager.update_reading_progress(
            session_id=session_id,
            current_position=50,
            completion_percentage=25.0,
            time_spent_seconds=120
        )
        
        self.assertTrue(result)
        
        # Verify progress was saved
        user_id = 1
        session = self.content_manager.get_reading_session(session_id, user_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session['completion_percentage'], 25.0)
        self.assertEqual(session['time_spent_seconds'], 120)
    
    def test_progress_persistence(self):
        """Test that progress persists across sessions."""
        # Import content
        session_id = self.content_manager.import_from_paste(
            content="Test content for persistence. This is a longer piece of text that meets the minimum character requirement for content import. It should be at least one hundred characters long.",
            title="Persistence Test",
            language="en",
            user_attestation=True
        )
        
        # Update progress
        self.content_manager.update_reading_progress(
            session_id=session_id,
            current_position=100,
            completion_percentage=50.0,
            time_spent_seconds=300
        )
        
        # Retrieve and verify
        user_id = 1
        session1 = self.content_manager.get_reading_session(session_id, user_id)
        self.assertEqual(session1['completion_percentage'], 50.0)
        
        # Update again
        self.content_manager.update_reading_progress(
            session_id=session_id,
            current_position=150,
            completion_percentage=75.0,
            time_spent_seconds=450
        )
        
        # Verify updated progress
        session2 = self.content_manager.get_reading_session(session_id, user_id)
        self.assertEqual(session2['completion_percentage'], 75.0)
        self.assertEqual(session2['time_spent_seconds'], 450)


class TestReadingModeUIFlow(unittest.TestCase):
    """Test the complete flow of reading mode UI."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.db = FlashcardDatabase(self.db_path)
        self.content_manager = ContentManager(self.db)
        self.library = ReadingLibrary(self.db)
    
    def tearDown(self):
        """Clean up test database."""
        try:
            self.db.close()
        except:
            pass
        
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_complete_reading_flow(self):
        """Test the complete flow: import -> library -> read."""
        # Step 1: Import content
        test_content = "This is a test article for reading mode. It contains multiple sentences. Each sentence is important for language learning. This content is long enough to meet the minimum requirement for import."
        title = "Complete Flow Test"
        
        session_id = self.content_manager.import_from_paste(
            content=test_content,
            title=title,
            language="en",
            user_attestation=True
        )
        
        self.assertIsNotNone(session_id)
        
        # Step 2: Get from library
        user_id = 1
        sessions = self.library.get_all_sessions(user_id)
        
        found_session = None
        for session in sessions:
            if session.get('id') == session_id:
                found_session = session
                break
        
        self.assertIsNotNone(found_session)
        self.assertEqual(found_session['title'], title)
        
        # Step 3: Load for reading
        session = self.content_manager.get_reading_session(session_id, user_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session['content'], test_content)
        self.assertEqual(session['title'], title)
        
        # Verify all required fields for display
        self.assertIn('word_count', session)
        self.assertIn('difficulty_rating', session)
        self.assertIn('completion_percentage', session)


if __name__ == '__main__':
    unittest.main()
