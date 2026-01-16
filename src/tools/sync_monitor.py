"""
Sync Queue Monitor
------------------
Watches the 'pending_sync_actions' table for new items from the mobile app.
This is a developer tool to verify that sync is working.

Usage:
    python src/tools/sync_monitor.py
"""

import sqlite3
import time
import os
import sys

# Add parent dir to path to allow imports if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

DB_PATH = "flashcards.db"

def get_pending_count(cursor):
    try:
        cursor.execute("SELECT COUNT(*) FROM pending_sync_actions WHERE status='pending'")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0

def get_latest_pending(cursor, limit=5):
    try:
        cursor.execute("""
            SELECT id, action_type, payload, created_at 
            FROM pending_sync_actions 
            WHERE status='pending' 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    print("--- Sync Queue Monitor ---")
    print(f"Watching {DB_PATH} for new actions...")
    print("Press Ctrl+C to exit.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    last_count = -1
    
    try:
        while True:
            current_count = get_pending_count(cursor)
            
            if current_count != last_count:
                print(f"[{time.strftime('%H:%M:%S')}] Pending Actions: {current_count}")
                if current_count > 0:
                    rows = get_latest_pending(cursor)
                    for row in rows:
                        print(f"  > ID: {row[0]} | Type: {row[1]} | Payload: {row[2][:50]}...")
                last_count = current_count
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
