import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager

def test_language_mapping():
    print("=== Testing Study Language Mapping ===")
    
    # 1. Setup Mock DB
    db_path = "test_lang.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = FlashcardDatabase(db_path)
    
    # 2. Init Manager
    mgr = StudyManager(db)
    
    # 3. Test Cases
    cases = [
        ("Spanish", "es"),
        ("Korean", "ko"),
        ("French", "fr"),
        ("Japanese", "ja"),
        ("UnknownLang", "es"), # Default
        ("German", "de")
    ]
    
    for input_name, expected_code in cases:
        mgr.study_language = input_name
        code = mgr.get_study_language_code()
        
        if code == expected_code:
            print(f"✅ '{input_name}' mapped to '{code}'")
        else:
            print(f"❌ '{input_name}' FAILED: expected '{expected_code}', got '{code}'")
            sys.exit(1)
            
    # Clean up
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== MAPPING VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    test_language_mapping()
