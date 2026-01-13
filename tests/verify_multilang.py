
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager

def verify_multilang():
    print("VERIFYING MULTI-LANGUAGE SUPPORT...")
    
    # Use a test DB
    db_path = "test_multilang.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = FlashcardDatabase(db_path)
    sm = StudyManager(db)
    
    print("\n1. Testing Deck Language Scoping...")
    # Create decks
    d1 = db.create_deck("French Verbs", "Basic French", language="French")
    d2 = db.create_deck("German Nouns", "Basic German", language="German")
    d3 = db.create_deck("General", "No language") # language=None
    
    # Filter French
    decks_fr = db.get_all_decks(language="French")
    print(f"French decks: {[d['name'] for d in decks_fr]}")
    assert len(decks_fr) == 1 and decks_fr[0]['name'] == "French Verbs"
    
    # Filter German
    decks_de = db.get_all_decks(language="German")
    print(f"German decks: {[d['name'] for d in decks_de]}")
    assert len(decks_de) == 1 and decks_de[0]['name'] == "German Nouns"
    
    # No filter (all)
    decks_all = db.get_all_decks()
    print(f"All decks: {[d['name'] for d in decks_all]}")
    assert len(decks_all) == 3
    
    print("✓ Deck scoping passed!")
    
    print("\n2. Testing Imported Content Scoping...")
    # Add imports
    id1 = db.add_imported_content("word", "bonjour", "url1", language="French")
    print(f"Added 'bonjour', id={id1}")
    id2 = db.add_imported_content("word", "guten tag", "url2", language="German")
    print(f"Added 'guten tag', id={id2}")
    id3 = db.add_imported_content("word", "hello", "url3", language="English")
    print(f"Added 'hello', id={id3}")
    
    # IMMEDIATE VERIFICATION
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, content, language FROM imported_content")
    fresh_rows = cursor.fetchall()
    print(f"DEBUG: Immediate fetch after insert: {fresh_rows}")
    
    # Test StudyManager filtering
    print("Setting study language to 'French'...")
    sm.set_study_language("French")
    
    # DEBUG: Print everything in imported_content
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM imported_content")
    rows = cursor.fetchall()
    print(f"DEBUG: All imported content before query: {rows}")
    
    words_fr = sm.get_imported_words()
    print(f"French words: {[w['word'] for w in words_fr]}")
    assert len(words_fr) == 1 and words_fr[0]['word'] == "bonjour"
    
    print("Setting study language to 'German'...")
    sm.set_study_language("German")
    words_de = sm.get_imported_words()
    print(f"German words: {[w['word'] for w in words_de]}")
    assert len(words_de) == 1 and words_de[0]['word'] == "guten tag"
    
    print("✓ Content scoping passed!")
    
    # Clean up
    db.close()
    # if os.path.exists(db_path):
    #     os.remove(db_path)
    print("\nALL CHECKS PASSED")

if __name__ == "__main__":
    verify_multilang()
