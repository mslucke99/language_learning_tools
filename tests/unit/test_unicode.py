import unittest
import os
import sqlite3
from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager

class TestUnicode(unittest.TestCase):
    def setUp(self):
        self.db_path = 'databases/test_unicode_unit.db'
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = FlashcardDatabase(self.db_path)
        self.sm = StudyManager(self.db)

    def tearDown(self):
        self.db.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_unicode_storage_and_retrieval(self):
        test_cases = [
            {'lang': 'Korean', 'text': '열왕을 멸시하며 방백을 치소하며', 'type': 'sentence'},
            {'lang': 'Japanese', 'text': '私は言語を学んでいます。', 'type': 'word'},
            {'lang': 'Arabic', 'text': 'أنا أتعلم اللغات.', 'type': 'sentence'},
            {'lang': 'French', 'text': 'Le français est une belle langue.', 'type': 'sentence'}
        ]

        for case in test_cases:
            content_id = self.db.add_imported_content(
                content_type=case['type'],
                content=case['text'],
                url=f'http://test.com/{case["lang"]}',
                title=f'Test {case["lang"]}'
            )
            self.assertIsNotNone(content_id)

        # Verify retrieval via StudyManager
        sentences = self.sm.get_imported_sentences()
        words = self.sm.get_imported_words()

        sentence_texts = [s['sentence'] for s in sentences]
        word_texts = [w['word'] for w in words]

        self.assertIn('열왕을 멸시하며 방백을 치소하며', sentence_texts)
        self.assertIn('أنا أتعلم اللغات.', sentence_texts)
        self.assertIn('私は言語を学んでいます。', word_texts)

if __name__ == '__main__':
    unittest.main()
