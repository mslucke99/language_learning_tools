import os
import sqlite3
from src.core.database import FlashcardDatabase

def test_db():
    db_path = "minimal_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("Testing DB initialization...")
    db = FlashcardDatabase(db_path)
    print("DB initialized.")
    
    print("Adding known word 'apple'...")
    db.add_known_word("apple", "en")
    print("Is apple known?", db.is_word_known("apple", "en"))
    
    print("Adding non-word 'xyzzy'...")
    db.add_ignored_word("xyzzy", "en")
    print("Is xyzzy known?", db.is_word_known("xyzzy", "en"))
    print("Is xyzzy ignored?", len(db.get_all_ignored_words("en")) == 1)
    
    count = db.get_known_word_count("en")
    print(f"Known word count: {count}")
    
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_db()
