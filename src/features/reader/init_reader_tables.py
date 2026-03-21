"""
Initialize reader tables in the database.

This script creates the story_sessions, story_passages, and story_templates
tables if they don't already exist.
"""

import sqlite3
import os

def init_reader_tables(db_path: str = None):
    """
    Initialize reader tables in the database.
    
    Args:
        db_path: Optional path to database file
    """
    # Use default database path if not provided
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), '../../../flashcards.db')
    
    print(f"Initializing reader tables in: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create story_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT NOT NULL,
            genre TEXT NOT NULL,
            generation_mode TEXT NOT NULL,
            current_passage_id INTEGER,
            story_context TEXT NOT NULL,
            vocabulary_introduced TEXT,
            created_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (current_passage_id) REFERENCES story_passages (id)
        )
    """)
    print("  ✓ story_sessions table created")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_story_sessions_language ON story_sessions(language)")
    
    # Create story_passages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            passage_number INTEGER NOT NULL,
            story_text TEXT NOT NULL,
            new_words TEXT NOT NULL,
            choices TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES story_sessions (id) ON DELETE CASCADE
        )
    """)
    print("  ✓ story_passages table created")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_story_passages_session ON story_passages(session_id)")
    
    # Create story_templates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre TEXT NOT NULL,
            node_id TEXT NOT NULL,
            template_text TEXT NOT NULL,
            suggested_vocab TEXT,
            choices TEXT NOT NULL,
            metadata TEXT,
            UNIQUE(genre, node_id)
        )
    """)
    print("  ✓ story_templates table created")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_story_templates_genre ON story_templates(genre)")
    
    # Create sentence_embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentence_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            sentence_text TEXT NOT NULL,
            embedding_blob BLOB NOT NULL,
            model_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES reading_sessions(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ sentence_embeddings table created")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentence_embeddings_session ON sentence_embeddings(session_id)")
    
    conn.commit()
    conn.close()
    
    print("\nReader tables initialized successfully!")

if __name__ == "__main__":
    init_reader_tables()
