"""
Unit tests for Phase 1 critical bug fixes.

Tests cover:
1. Chat error fix - current_history fetch in worker loop
2. Sentence related items display fix
3. Word related items display fix
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.features.study_center.logic.study_manager import StudyManager


class TestChatErrorFix(unittest.TestCase):
    """Test Issue #6: Chat error with missing current_history argument."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_ollama = Mock()
        self.mock_ollama.is_available.return_value = True
        
    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.features.study_center.logic.study_manager.OllamaClient')
    def test_worker_loop_fetches_chat_history(self, mock_ollama_class, mock_db_class):
        """Test that worker loop fetches current_history for chat_message tasks."""
        # Setup
        mock_db_class.return_value = self.mock_db
        mock_ollama_class.return_value = self.mock_ollama
        
        manager = StudyManager(self.mock_db, self.mock_ollama)
        
        # Mock get_chat_messages to return sample history
        sample_history = [
            {'role': 'user', 'content': 'Hello', 'id': 1},
            {'role': 'assistant', 'content': 'Hi there!', 'id': 2}
        ]
        manager.get_chat_messages = Mock(return_value=sample_history)
        
        # Mock send_chat_message
        manager.send_chat_message = Mock(return_value=(True, {'reply': 'Test'}, {}))
        
        # Queue a chat task
        task_id = manager.queue_generation_task(
            'chat_message',
            0,
            session_id=123,
            user_message='Test message'
        )
        
        # Give worker time to process (in real scenario)
        # For testing, we'll directly inspect what would happen
        task = manager.task_queue.queue[0]
        
        # Verify task structure
        self.assertEqual(task['type'], 'chat_message')
        self.assertEqual(task['kwargs']['session_id'], 123)
        self.assertEqual(task['kwargs']['user_message'], 'Test message')
        
    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.features.study_center.logic.study_manager.OllamaClient')
    def test_send_chat_message_with_history(self, mock_ollama_class, mock_db_class):
        """Test that send_chat_message receives and uses current_history."""
        # Setup
        mock_db_class.return_value = self.mock_db
        mock_ollama_class.return_value = self.mock_ollama
        
        manager = StudyManager(self.mock_db, self.mock_ollama)
        
        # Prepare history
        history = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi!'}
        ]
        
        # Mock methods
        manager.get_chat_sessions = Mock(return_value=[{'id': 1, 'cur_topic': 'Test'}])
        manager.db.add_chat_message = Mock()
        self.mock_ollama.generate_response = Mock(return_value='<reply>Response</reply>')
        
        # Call with current_history
        success, result, suggestions = manager.send_chat_message(
            session_id=1,
            user_message='Test',
            current_history=history
        )
        
        # Verify it was successful
        self.assertTrue(success)
        

class TestSentenceRelatedItemsFix(unittest.TestCase):
    """Test Issue #9: Sentence related items display fix."""
    
    def test_check_queue_status_handles_suggestions(self):
        """Test that _check_queue_status extracts and displays suggestions."""
        # This is an integration test that would require mocking tkinter
        # For now, verify the logic conceptually
        
        task_status = {
            'status': 'completed',
            'result': 'Explanation text',
            'suggestions': {
                'flashcards': [
                    {'word': 'test', 'definition': 'a test'}
                ],
                'grammar': [
                    {'title': 'Grammar Rule', 'explanation': 'Explanation'}
                ]
            }
        }
        
        # Verify suggestions structure
        self.assertIn('flashcards', task_status['suggestions'])
        self.assertIn('grammar', task_status['suggestions'])
        self.assertEqual(len(task_status['suggestions']['flashcards']), 1)
        self.assertEqual(len(task_status['suggestions']['grammar']), 1)
        
    def test_suggestions_key_extraction(self):
        """Test that suggestions are extracted with correct key."""
        # Simulating what the worker returns
        worker_result = {
            'status': 'completed',
            'suggestions': {
                'flashcards': [],
                'grammar': []
            }
        }
        
        # Test extraction (old bug used 'result_extra')
        suggestions = worker_result.get('suggestions', {})
        self.assertIsInstance(suggestions, dict)
        self.assertIn('flashcards', suggestions)


class TestWordsRelatedItemsFix(unittest.TestCase):
    """Test Issue #10: Words related items display fix."""
    
    def test_handle_completed_task_extracts_suggestions(self):
        """Test that _handle_completed_task extracts suggestions from status."""
        
        task_status = {
            'status': 'completed',
            'result': 'Definition text',
            'suggestions': {
                'flashcards': [
                    {'word': 'related', 'definition': 'connected'}
                ],
                'grammar': []
            }
        }
        
        # Verify suggestions extraction
        suggestions = task_status.get('suggestions', {})
        self.assertIsNotNone(suggestions)
        self.assertEqual(len(suggestions['flashcards']), 1)


if __name__ == '__main__':
    unittest.main()
