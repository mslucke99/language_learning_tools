import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

import sqlite3
import firebase_admin
import uuid
from datetime import datetime
from firebase_admin import credentials, firestore
from src.services.firebase_config import initialize_firebase, get_firestore_client
from src.services.sync_merger import SYNCABLE_TABLES

def migrate_to_firestore(db_path: str):
    print(f"Starting migration from {db_path} to Firestore...")
    
    # Init Firebase
    db = initialize_firebase()
    if not db:
        print("Failed to initialize Firebase. Check logs/config.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_uploaded = 0
    
    for table in SYNCABLE_TABLES:
        print(f"Migrating table: {table}...")
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            batch = db.batch()
            count = 0
            table_total = 0
            
            for row in rows:
                data = dict(row)
                row_uuid = data.get('uuid')
                
                # If UUID is missing, generate one and update local DB
                if not row_uuid:
                    row_uuid = str(uuid.uuid4())
                    data['uuid'] = row_uuid
                    if 'last_modified' not in data or not data['last_modified']:
                        data['last_modified'] = datetime.now().isoformat()
                    
                    # Update local database so we don't generate a new one next time
                    print(f"  Generating UUID for {table} ID {data['id']}: {row_uuid}")
                    try:
                        conn.execute(
                            f"UPDATE {table} SET uuid = ?, last_modified = ? WHERE id = ?",
                            (row_uuid, data['last_modified'], data['id'])
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"  Warning: Could not update local row with new UUID: {e}")
                
                doc_ref = db.collection(table).document(row_uuid)
                batch.set(doc_ref, data)
                count += 1
                table_total += 1
                total_uploaded += 1
                
                if count >= 400: # Firestore batch limit is 500
                    batch.commit()
                    batch = db.batch()
                    count = 0
                    print(f"  Committed batch for {table}...")

            if count > 0:
                batch.commit()
                
            print(f"  Finished {table}: {table_total} records.")
            
        except sqlite3.OperationalError:
            print(f"  Table {table} not found in local DB. Skipping.")
        except Exception as e:
            print(f"  Error migrating {table}: {e}")

    print(f"Migration complete. Total records uploaded: {total_uploaded}")

if __name__ == "__main__":
    # Default to current dir flashcards.db
    db_path = "flashcards.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
    else:
        migrate_to_firestore(db_path)
