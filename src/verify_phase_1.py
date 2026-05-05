import sys
import os
# Ensure src is in path if run from language_learning_tools root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import FlashcardDatabase
import sqlite3

def verify_phase_1():
    db = FlashcardDatabase()
    conn = db.conn
    cursor = conn.cursor()
    
    print("--- Verifying Database Schema ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentence_embeddings'")
    if cursor.fetchone():
        print("[OK] sentence_embeddings table exists.")
    else:
        print("[FAIL] sentence_embeddings table missing.")
        return

    print("\n--- Verifying Cascading Delete ---")
    # 1. Insert a test reading session
    cursor.execute("""
        INSERT INTO reading_sessions (title, content, language, source, import_method, legal_attestation)
        VALUES ('Test Book', 'This is a test sentence.', 'en', 'test', 'paste', 1)
    """)
    session_id = cursor.lastrowid
    print(f"Inserted test session ID: {session_id}")
    
    # 2. Insert a test embedding
    cursor.execute("""
        INSERT INTO sentence_embeddings (session_id, sentence_text, embedding_blob, model_name)
        VALUES (?, 'This is a test sentence.', ?, 'test-model')
    """, (session_id, b'dummy-vector'))
    print(f"Inserted test embedding for session {session_id}")
    
    # 3. Verify embedding exists
    cursor.execute("SELECT COUNT(*) FROM sentence_embeddings WHERE session_id = ?", (session_id,))
    count = cursor.fetchone()[0]
    print(f"Embedding count before delete: {count}")
    
    # 4. Delete the session
    print("Deleting session...")
    db.delete_reading_session(session_id)
    
    # 5. Verify embedding is gone
    cursor.execute("SELECT COUNT(*) FROM sentence_embeddings WHERE session_id = ?", (session_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        print("[OK] Cascading delete worked. Embedding was removed.")
    else:
        print(f"[FAIL] Cascading delete FAILED. Embedding still exists (count: {count}).")

    print("\n--- Verifying Background Worker Logic ---")
    cursor.execute("""
        INSERT INTO reading_sessions (title, content, language, source, import_method, legal_attestation)
        VALUES ('Worker Test', 'Sentence 1. Sentence 2.', 'en', 'test', 'paste', 1)
    """)
    worker_session_id = cursor.lastrowid
    
    ids = db.get_sessions_needing_embeddings()
    if worker_session_id in ids:
        print(f"[OK] New session {worker_session_id} identified for background processing.")
    else:
        print(f"[FAIL] New session {worker_session_id} NOT found in pending list.")

    # Cleanup
    db.delete_reading_session(worker_session_id)
    db.close()

if __name__ == "__main__":
    verify_phase_1()
