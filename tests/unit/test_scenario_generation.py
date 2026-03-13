import unittest
from unittest.mock import Mock, patch
import sys
import os
import re

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.features.study_center.logic.study_manager import StudyManager
import json

class TestScenarioGeneration(unittest.TestCase):
    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.services.llm_service.get_ai_client')
    def test_generate_roleplay_scenario_success(self, mock_get_ai_client, mock_db_class):
        # Setup mocks
        mock_db = Mock()
        # Mock DB config loading
        mock_db.conn.cursor.return_value.fetchone.return_value = None
        mock_db.get_setting.return_value = None
        
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        mock_get_ai_client.return_value = mock_ollama
        
        # Mock AI response
        mock_response = """
        {
          "name": "Fantasy Quest",
          "description": "A journey to the crystal mountain",
          "situation": "You are at a tavern in the village of Eldoria.",
          "user_role": "A wandering mage",
          "characters": [
            {
              "name": "Thrain",
              "role": "Dwarf Warrior",
              "personality": "Gruff but loyal"
            }
          ]
        }
        """
        mock_ollama.generate_response.return_value = mock_response
        
        manager = StudyManager(mock_db, mock_ollama)
        manager.study_language = "Korean"
        manager.native_language = "English"
        
        success, data = manager.generate_roleplay_scenario("Fantasy World")
        
        self.assertTrue(success)
        self.assertEqual(data['name'], "Fantasy Quest")
        self.assertEqual(data['user_role'], "A wandering mage")
        self.assertEqual(len(data['characters']), 1)
        self.assertEqual(data['characters'][0]['name'], "Thrain")
        
        # Verify prompt formatting (basic check)
        mock_ollama.generate_response.assert_called_once()
        prompt = mock_ollama.generate_response.call_args[0][0]
        self.assertIn("Fantasy World", prompt)
        self.assertIn("Korean", prompt)

    @patch('src.features.study_center.logic.study_manager.FlashcardDatabase')
    @patch('src.services.llm_service.get_ai_client')
    def test_generate_roleplay_scenario_failure(self, mock_get_ai_client, mock_db_class):
        mock_db = Mock()
        # Mock DB config loading
        mock_db.conn.cursor.return_value.fetchone.return_value = None
        mock_db.get_setting.return_value = None
        
        mock_ollama = Mock()
        mock_ollama.is_available.return_value = True
        mock_get_ai_client.return_value = mock_ollama
        mock_ollama.is_available.return_value = True
        mock_ollama.generate_response.return_value = None
        
        manager = StudyManager(mock_db, mock_ollama)
        
        success, data = manager.generate_roleplay_scenario("Everyday Life")
        
        self.assertFalse(success)
        self.assertIn("error", data)

if __name__ == '__main__':
    unittest.main()
