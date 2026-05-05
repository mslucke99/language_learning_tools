#!/usr/bin/env python
"""
Test script for sentence splitting with Korean and Chinese text
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

def test_korean_chinese():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test cases with actual Korean and Chinese text
    test_cases = [
        # Korean
        {
            'lang': 'Korean',
            'text': "안녕하세요. 어떻게 지내세요? 저는 잘 지내요.",
            'expected': 3,
            'desc': "Korean sentences with periods and question marks"
        },
        # Chinese
        {
            'lang': 'Chinese',
            'text': "你好。怎么样？我很好。",
            'expected': 3,
            'desc': "Chinese sentences with fullwidth punctuation"
        },
        # Mixed Korean and English
        {
            'lang': 'Mixed Korean-English',
            'text': "Hello world. 안녕하세요. How are you? 어떻게 지내세요?",
            'expected': 4,
            'desc': "Mixed English and Korean sentences"
        },
        # Mixed Chinese and English
        {
            'lang': 'Mixed Chinese-English',
            'text': "Hello world. 你好。How are you? 怎么样？",
            'expected': 4,
            'desc': "Mixed English and Chinese sentences"
        },
        # Newlines with Korean
        {
            'lang': 'Korean with newlines',
            'text': "첫 번째 문장입니다.\n두 번째 문장입니다.\n\n새로운 단락입니다.",
            'expected': 3,
            'desc': "Korean sentences with newlines and paragraph break"
        }
    ]
    
    print("Testing Korean and Chinese sentence splitting:\n")
    
    for i, case in enumerate(test_cases):
        print(f"--- Test {i+1}: {case['lang']} ---")
        print(f"Description: {case['desc']}")
        print(f"Text length: {len(case['text'])} characters")
        
        try:
            sentences = miner._split_sentences(case['text'])
            print(f"Output count: {len(sentences)} (expected: {case['expected']})")
            
            # Show first few characters of each sentence for verification
            if sentences:
                sentence_previews = []
                for s in sentences[:3]:  # Show first 3 sentences
                    preview = s[:30] + "..." if len(s) > 30 else s
                    sentence_previews.append(repr(preview))
                print(f"Sentence previews: [{', '.join(sentence_previews)}]")
                if len(sentences) > 3:
                    print(f"... and {len(sentences) - 3} more")
            
            if len(sentences) == case['expected']:
                print("✓ PASS")
            else:
                print("✗ FAIL - Count mismatch")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            
        print()

if __name__ == "__main__":
    test_korean_chinese()