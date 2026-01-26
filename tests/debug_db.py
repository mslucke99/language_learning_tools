
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.core.database import FlashcardDatabase

def debug():
    db_path = "debug_mini.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = FlashcardDatabase(db_path)
    print("DB created. Adding content...")
    
    try:
        id1 = db.add_imported_content("word", "test", "url_x", language="French")
        print(f"Added ID: {id1}")
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM imported_content")
        print(f"Rows: {cursor.fetchall()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    debug()
