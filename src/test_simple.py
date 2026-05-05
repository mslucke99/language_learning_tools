#!/usr/bin/env python
"""
Simple test script for sentence splitting - avoids Unicode printing issues
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

def test_basic():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test cases using ASCII to avoid encoding issues
    test_cases = [
        ("English. Sentences. Here.", 3, "English periods"),
        ("안녕하세요. 어떻게. 지내세요.", 3, "Korean periods - simulated"),
        ("Hello. 안녕. World. 테스트.", 4, "Mixed English-Korean - simulated"),
        ("Dr. Smith went to the U.S.A. He saw Mr. Jones.", 2, "With abbreviations"),
        ("Price is $3.99. That's expensive.", 2, "With decimals"),
        ("Line one.\nLine two.\n\nParagraph two.", 3, "Newline handling"),
    ]
    
    print("Running sentence splitting tests...")
    print("=" * 50)
    
    all_passed = True
    
    for i, (text, expected, description) in enumerate(test_cases):
        try:
            sentences = miner._split_sentences(text)
            actual = len(sentences)
            
            if actual == expected:
                status = "PASS"
            else:
                status = f"FAIL (got {actual}, expected {expected})"
                all_passed = False
                
            print(f"Test {i+1:2d} [{status}] {description}")
            
        except Exception as e:
            print(f"Test {i+1:2d} [ERROR] {description}: {e}")
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    
    return all_passed

if __name__ == "__main__":
    success = test_basic()
    sys.exit(0 if success else 1)