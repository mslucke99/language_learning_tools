import sys
import os
import sqlite3
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import FlashcardDatabase
from src.services.text.vocab_calibration import VocabCalibrationService

def test_download():
    print("=== Testing Frequency List Download ===")
    
    # 1. Setup Mock DB
    db_path = "test_download.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = FlashcardDatabase(db_path)
    
    # 2. Clear cache to force download
    cache_dir = os.path.join(os.path.dirname(db_path), "cache", "frequency_lists")
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
        print("Cleared cache.")
        
    # 3. Init Service
    service = VocabCalibrationService(db)
    
    # Prune existing logs for this test
    logging.basicConfig(level=logging.INFO)
    
    # 4. Test Korean
    print("\nAttempting to download Korean (ko) list...")
    words = service._get_frequency_list("ko")
    
    if words and len(words) > 0:
        print(f"✅ Successfully downloaded Korean list! (First 5 words: {words[:5]})")
    else:
        print("❌ FAILED to download Korean list.")
        sys.exit(1)
        
    # 5. Test Spanish
    print("\nAttempting to download Spanish (es) list...")
    words_es = service._get_frequency_list("es")
    if words_es and len(words_es) > 0:
        print(f"✅ Successfully downloaded Spanish list! (First 5 words: {words_es[:5]})")
    else:
        print("❌ FAILED to download Spanish list.")
        sys.exit(1)

    # Clean up
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== DOWNLOAD VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    test_download()
