#!/usr/bin/env python
"""
Simple debug script for sentence splitting - avoids Unicode printing issues
"""
import sys
import os

# Add the root directory (parent of src) to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.text.sentence_miner import SentenceMiner
from core.database import FlashcardDatabase

# Mock database for testing
class MockDatabase:
    def get_all_known_words(self, lang_code):
        return []  # Empty for testing
    
    def get_all_ignored_words(self, lang_code):
        return []  # Empty for testing

def debug_simple():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test case
    text = "Dr. Smith went to the U.S.A. He saw Mr. Jones."
    print(f"Testing: {repr(text)}")
    
    try:
        sentences = miner._split_sentences(text)
        print(f"Result: {sentences}")
        print(f"Count: {len(sentences)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_simple()