#!/usr/bin/env python
"""
Test script for sentence splitting functionality
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import using relative paths that work with the package structure
try:
    from services.text.sentence_miner import SentenceMiner
    from core.database import FlashcardDatabase
except ImportError:
    # Fallback for when running from src directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from services.text.sentence_miner import SentenceMiner
    from core.database import FlashcardDatabase

# Mock database for testing
class MockDatabase:
    def get_all_known_words(self, lang_code):
        return []  # Empty for testing
    
    def get_all_ignored_words(self, lang_code):
        return []  # Empty for testing

# Test the sentence splitter
def test_split_sentences():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test cases - using simple ASCII text to avoid encoding issues
    test_texts = [
        # English
        "Hello world. How are you? I'm fine!",
        
        # Simulated Korean with ASCII placeholders
        "Hello. How are you? I am fine.",
        
        # Mixed English and placeholders
        "Hello world. Placeholder. How are you? Placeholder again.",
        
        # With abbreviations
        "Dr. Smith went to the U.S.A. He saw Mr. Jones.",
        
        # With decimals (should not split)
        "The price is $3.99. That's expensive.",
        
        # Newline handling
        "This is sentence one.\nThis is sentence two.\n\nThis is a new paragraph.",
        
        # Simulated CJK with ASCII placeholders
        "First sentence. Second sentence! Third sentence?",
        
        # Edge cases
        "...",  # Just ellipsis
        "!!! ???",  # Multiple punctuation
        "No punctuation here",  # No punctuation
        "Single word.",  # Single word with period
    ]
    
    # Test case descriptions for printing
    descriptions = [
        "English sentences",
        "Simulated Korean (ASCII)", 
        "Mixed English and placeholders",
        "With abbreviations",
        "With decimals (should not split)",
        "Newline handling",
        "Simulated CJK (ASCII)",
        "Ellipsis only",
        "Multiple punctuation",
        "No punctuation",
        "Single word with period"
    ]
    
    print("Testing sentence splitting functionality:\n")
    
    for i, (text, desc) in enumerate(zip(test_texts, descriptions)):
        print(f"--- Test {i+1}: {desc} ---")
        print(f"Input: {repr(text)}")
        
        try:
            sentences = miner._split_sentences(text)
            print(f"Output: {sentences}")
            print(f"Count: {len(sentences)}")
            
            # Validate that we didn't create empty strings
            empty_count = sum(1 for s in sentences if not s.strip())
            if empty_count > 0:
                print(f"WARNING: Found {empty_count} empty sentences!")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            
        print()

if __name__ == "__main__":
    test_split_sentences()