import os
import sqlite3
import pytest
from src.core.database import FlashcardDatabase
from src.services.text.sentence_miner import SentenceMiner
from src.services.text.tokenizer_service import TokenizerService

@pytest.fixture
def temp_db():
    db_path = "test_nonword.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = FlashcardDatabase(db_path)
    yield db
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)

def test_ignored_words_db(temp_db):
    # 1. Add known word
    print("Step 1: Adding apple")
    temp_db.add_known_word("apple", "en")
    is_known = temp_db.is_word_known("apple", "en")
    print(f"Step 1: is_known={is_known}")
    assert is_known is True
    
    # 2. Add ignored word (non-word)
    print("Step 2: Adding xyzzy as ignored")
    temp_db.add_ignored_word("xyzzy", "en")
    is_xyzzy_known = temp_db.is_word_known("xyzzy", "en")
    print(f"Step 2: is_xyzzy_known={is_xyzzy_known}")
    assert is_xyzzy_known is False 
    
    # 3. Mark known word as ignored
    print("Step 3: Marking apple as ignored")
    temp_db.add_ignored_word("apple", "en")
    is_apple_known_now = temp_db.is_word_known("apple", "en")
    print(f"Step 3: is_apple_known_now={is_apple_known_now}")
    assert is_apple_known_now is False

if __name__ == "__main__":
    db_path = "test_manual_final.db"
    if os.path.exists(db_path): os.remove(db_path)
    db = FlashcardDatabase(db_path)
    try:
        test_ignored_words_db(db)
        print("Test PASSED!")
    finally:
        db.close()
        if os.path.exists(db_path): os.remove(db_path)

if __name__ == "__main__":
    # Quick manual run if pytest not desired
    db = FlashcardDatabase("test_manual.db")
    try:
        test_ignored_words_db(db)
        print("DB test passed!")
        test_sentence_miner_ignore(db)
        print("Miner test passed!")
    finally:
        db.close()
        if os.path.exists("test_manual.db"):
            os.remove("test_manual.db")
