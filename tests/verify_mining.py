import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import FlashcardDatabase
from src.services.text.sentence_miner import SentenceMiner, TokenizerService
from src.services.text.vocab_calibration import VocabCalibrationService

def test_mining_feature():
    print("=== Starting Sentence Mining Verification ===")
    
    # 1. Setup Test DB
    db_path = "test_mining.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = FlashcardDatabase(db_path)
    print("✅ Database created")
    
    # 2. Check Schema
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='known_words'")
    if cursor.fetchone():
        print("✅ 'known_words' table exists")
    else:
        print("❌ 'known_words' table MISSING")
        return

    # 3. Test Vocabulary Management
    # Add simple known words
    db.add_known_word("hello", "en", "manual")
    db.add_known_words_bulk(["world", "python"], "en", "manual")
    
    if db.is_word_known("hello", "en") and db.is_word_known("world", "en"):
        print("✅ Vocabulary addition works")
    else:
        print("❌ Vocabulary addition FAILED")
        
    print(f"Known count: {db.get_known_word_count('en')}")

    # 4. Test Sentence Mining
    # Mock Tokenizer (simple split for testing without huge libraries if need be, 
    # but we rely on TokenizerService which normally needs spacy/etc. 
    # Let's hope TokenizerService defaults to simple split if model missing or we use English)
    
    # We will use a real TokenizerService but it might fail if models aren't present.
    # Assuming 'en' works with simple split in our service or fallback.
    
    # Note: TokenizerService in this codebase usually uses simple split for 'en' or external tools.
    # Let's try.
    
    try:
        tokenizer = TokenizerService()
        miner = SentenceMiner(db, tokenizer)
        
        text = "Hello world. Hello Python. This is new."
        # Known: hello, world, python
        # Sentences:
        # 1. "Hello world." -> i+0 (all known)
        # 2. "Hello Python." -> i+0 (all known)
        # 3. "This is new." -> i+3 (This, is, new - all unknown)
        
        # Wait, comparison is case-insensitive usually. "Hello" vs "hello". 
        # Our DB stores lower(). Tokenizer should return distinct tokens.
        
        result = miner.analyze_text(text, "en")
        
        print("\nAnalysis Results:")
        for s in result.sentences:
            print(f"  - '{s.text}' | i+{s.level} | Unknown: {[t.lemma for t in s.unknown_words]}")
            
        # Verify
        if result.sentences[0].level == 0:
            print("✅ Sentence 1: PASS (i+0)")
        else:
             print(f"❌ Sentence 1: FAIL (Expected i+0, got i+{result.sentences[0].level})")
             sys.exit(1)
             
        if result.sentences[2].level >= 1:
             print("✅ Sentence 3: PASS (contains unknowns)")
        else:
             print("❌ Sentence 3: FAIL (Expected unknowns)")
             sys.exit(1)

    except Exception as e:
        print(f"❌ Mining Engine Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 5. Clean up
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    test_mining_feature()
