
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.text.sentence_miner import SentenceMiner
from services.text.tokenizer_service import TokenizerService

class MockDB:
    def get_all_known_words(self, lang): return []

def test_refinements():
    miner = SentenceMiner(MockDB(), TokenizerService())
    
    # 1. Test _is_punctuation with numbers
    print("Testing _is_punctuation...")
    print(f"'123' is punctuation/number? {miner._is_punctuation('123')}")
    print(f"'2024' is punctuation/number? {miner._is_punctuation('2024')}")
    print(f"'Word' is punctuation/number? {miner._is_punctuation('Word')}")
    print(f"'Word123' is punctuation/number? {miner._is_punctuation('Word123')}")
    
    # 2. Test analysis on sentence with numbers
    text = "Year 2024 is here."
    # 'Year', 'is', 'here' -> 3 unknowns (assuming empty DB)
    # '2024' -> should be ignored
    
    result = miner.analyze_text(text, 'en')
    s = result.sentences[0]
    print(f"\nSentence: [{s.text}]")
    print(f"Unknowns: {[t.lemma for t in s.unknown_words]}")
    print(f"Level: {s.level} (Expected: 3)")
    
    # 3. Test filtering logic (simulated)
    # i+0: level == 0
    # i+1: level == 1
    # challenging: level >= 2
    
    print(f"\nFilter Check (Level {s.level}):")
    print(f"Is i+0? {s.level == 0}")
    print(f"Is i+1? {s.level == 1}")
    print(f"Is Challenging? {s.level >= 2}")

if __name__ == "__main__":
    test_refinements()
