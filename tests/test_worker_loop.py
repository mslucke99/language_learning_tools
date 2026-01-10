"""
Integration tests for StudyManager worker loop.

Tests the background task processing for various task types.
"""

import unittest
from unittest.mock import Mock, patch
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.features.study_center.logic.study_manager import StudyManager


class TestWorkerLoopIntegration(unittest.TestCase):
    """Integration tests for the worker loop task processing."""
    
    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.features.study_center.logic.study_manager.OllamaClient')
    def test_chat_task_includes_history_in_kwargs(self, mock_ollama_class, mock_db_class):
        """
        Test that when processing a chat_message task, the worker loop
        fetches current_history and includes it in kwargs before calling
        send_chat_message.
        """
        # Setup mocks
        mock_db = Mock()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        
        mock_db_class.return_value = mock_db
        mock_ollama_class.return_value = mock_ollama
        
        manager = StudyManager(mock_db, mock_ollama)
        
        # Mock the chat-related methods
        sample_history = [
            {'role': 'user', 'content': 'Hello', 'created_at': '2024-01-01'},
            {'role': 'assistant', 'content': 'Hi!', 'created_at': '2024-01-01'}
        ]
        manager.get_chat_messages = Mock(return_value=sample_history)
        manager.send_chat_message = Mock(return_value=(True, {'reply': 'Test reply'}, {}))
        
        # Queue a chat task
        task_id = manager.queue_generation_task(
            'chat_message',
            0,
            session_id=42,
            user_message='How are you?'
        )
        
        # Wait briefly for worker to process
        time.sleep(0.5)
        
        # Verify send_chat_message was called with current_history
        manager.send_chat_message.assert_called_once()
        call_kwargs = manager.send_chat_message.call_args[1]
        
        self.assertIn('current_history', call_kwargs)
        self.assertEqual(call_kwargs['current_history'], sample_history)
        self.assertEqual(call_kwargs['session_id'], 42)
        self.assertEqual(call_kwargs['user_message'], 'How are you?')
        
    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.features.study_center.logic.study_manager.OllamaClient')
    def test_sentence_explanation_returns_suggestions(self, mock_ollama_class, mock_db_class):
        """
        Test that sentence_explanation tasks return suggestions in the
        processing_results dictionary.
        """
        # Setup
        mock_db = Mock()
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        
        mock_db_class.return_value = mock_db
        mock_ollama_class.return_value = mock_ollama
        
        manager = StudyManager(mock_db, mock_ollama)
        
        # Mock generate_sentence_explanation
        test_suggestions = {
            'flashcards': [{'word': 'example', 'definition': 'a sample'}],
            'grammar': []
        }
        manager.generate_sentence_explanation = Mock(
            return_value=(True, 'Explanation text', test_suggestions)
        )
        
        # Queue task
        task_id = manager.queue_generation_task(
            'sentence_explanation',
            123,
            language='native',
            focus_areas=['all']
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Check results
        status = manager.get_task_status(task_id)
        self.assertEqual(status['status'], 'completed')
        self.assertIn('suggestions', status)
        self.assertEqual(status['suggestions'], test_suggestions)


if __name__ == '__main__':
    unittest.main()
