import sqlite3
from src.features.flashcards.logic.flashcard import Flashcard
from datetime import datetime
from typing import Optional, List, Dict

class FlashcardDatabase:
    def __init__(self, db_name="flashcards.db"):
        # check_same_thread=False allows the connection to be used across Flask request threads
        # This is safe for this application since we're not doing concurrent writes
        # isolation_level=None sets autocommit mode for immediate visibility across threads
        self.conn = sqlite3.connect(db_name, check_same_thread=False, isolation_level=None)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Create decks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                description TEXT,
                language TEXT
            )
        """)
        
        # Create flashcards table with deck_id foreign key
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                last_reviewed TEXT,
                easiness REAL DEFAULT 2.5,
                interval INTEGER DEFAULT 1,
                repetitions INTEGER DEFAULT 0,
                total_reviews INTEGER DEFAULT 0,
                correct_reviews INTEGER DEFAULT 0,
                FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
            )
        """)
        # Create imported_content table for browser extension imports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imported_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,  -- 'word', 'sentence', 'phrase'
                content TEXT NOT NULL,
                context TEXT,  -- surrounding text or sentence
                title TEXT,    -- page title if available
                url TEXT NOT NULL,
                language TEXT, -- target language
                created_at TEXT NOT NULL,
                processed INTEGER DEFAULT 0,  -- 0=not processed, 1=processed into flashcards
                tags TEXT     -- comma-separated tags
            )
        """)
        
        # Create word_definitions table for storing user-entered or AI-generated definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_content_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                definition TEXT NOT NULL,
                definition_language TEXT,  -- 'native' or language code
                source TEXT DEFAULT 'user',  -- 'user' or 'ollama'
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                examples TEXT,  -- JSON list of example sentences
                notes TEXT,  -- user notes
                difficulty_level INTEGER DEFAULT 0,  -- 0-5 difficulty scale
                FOREIGN KEY (imported_content_id) REFERENCES imported_content (id) ON DELETE CASCADE,
                UNIQUE(imported_content_id, definition_language)
            )
        """)
        
        # Create sentence_explanations table for AI-generated or user-entered explanations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentence_explanations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_content_id INTEGER NOT NULL,
                sentence TEXT NOT NULL,
                explanation TEXT NOT NULL,
                explanation_language TEXT,  -- 'native' or language code
                source TEXT DEFAULT 'user',  -- 'user' or 'ollama'
                focus_area TEXT,  -- 'grammar', 'vocabulary', 'context', 'all'
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                grammar_notes TEXT,  -- Specific grammar explanations
                user_notes TEXT,  -- User's own notes
                FOREIGN KEY (imported_content_id) REFERENCES imported_content (id) ON DELETE CASCADE
            )
        """)
        
        # Create study_settings table for user preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL
            )
        """)
        
        # Create grammar_followups table for follow-up questions on sentence explanations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grammar_followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sentence_explanation_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                context TEXT,  -- The original sentence for reference
                created_at TEXT NOT NULL,
                FOREIGN KEY (sentence_explanation_id) REFERENCES sentence_explanations (id) ON DELETE CASCADE
            )
        """)

        # Create grammar_book_entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grammar_book_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                language TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        # Create collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL, -- 'deck', 'word', 'sentence', 'grammar'
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                language TEXT,
                FOREIGN KEY (parent_id) REFERENCES collections (id) ON DELETE SET NULL
            )
        """)

        # Create writing_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS writing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                user_writing TEXT NOT NULL,
                feedback TEXT,
                grade TEXT,
                analysis TEXT, -- JSON blob for suggestions
                study_language TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Migration: Ensure analysis column exists for existing users
        try:
            cursor.execute("ALTER TABLE writing_sessions ADD COLUMN analysis TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Create chat_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cur_topic TEXT,
                study_language TEXT,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)

        # Create chat_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL, -- 'user' or 'assistant'
                content TEXT NOT NULL,
                analysis TEXT, -- JSON/XML blob for feedback/vocab
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
            )
        """)

        # Create quiz_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL, -- 'deck', 'vocab', 'grammar'
                source_id INTEGER,
                question_count INTEGER,
                difficulty TEXT,
                score INTEGER,
                total_questions INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        # Create quiz_questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                question_text TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                choice_a TEXT,
                choice_b TEXT,
                choice_c TEXT,
                choice_d TEXT,
                user_answer TEXT,
                is_correct INTEGER,
                FOREIGN KEY (session_id) REFERENCES quiz_sessions (id) ON DELETE CASCADE
            )
        """)

        # Create exam_attempts table for standardized test practice
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT NOT NULL,
                level TEXT,
                section TEXT,
                score INTEGER,
                total_questions INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        # Create exam_questions table for storing individual exam results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                choice_a TEXT,
                choice_b TEXT,
                choice_c TEXT,
                choice_d TEXT,
                user_answer TEXT,
                is_correct INTEGER,
                explanation TEXT,
                FOREIGN KEY (attempt_id) REFERENCES exam_attempts (id) ON DELETE CASCADE
            )
        """)

        # Migration: Add collection_id to existing tables
        self._migrate_schema()
        
        self.conn.commit()

    def _migrate_schema(self):
        """Add new columns to existing tables for backwards compatibility."""
        cursor = self.conn.cursor()
        
        # 1. Collection ID migrations
        migrations_collection = {
            "decks": "collection_id",
            "imported_content": "collection_id",
            "grammar_book_entries": "collection_id"
        }
        
        for table, column in migrations_collection.items():
            # Check if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if column not in columns:
                print(f"[DB] Migrating table {table}: adding {column}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER REFERENCES collections(id) ON DELETE SET NULL")

        # 2. Language ID migrations
        migrations_language = {
            "decks": "language",
            "collections": "language"
        }
        
        for table, column in migrations_language.items():
            # Check if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if column not in columns:
                print(f"[DB] Migrating table {table}: adding {column}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")

        self.conn.commit()

    def create_collection(self, name: str, type: str, parent_id: int = None, language: str = None) -> int:
        """Create a new collection and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO collections (name, type, parent_id, created_at, language) VALUES (?, ?, ?, ?, ?)",
            (name, type, parent_id, datetime.now().isoformat(), language)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_collections(self, type: str, language: str = None) -> list[dict]:
        """Get all collections of a specific type, optionally filtered by language."""
        cursor = self.conn.cursor()
        if language:
            cursor.execute("SELECT id, name, parent_id, language FROM collections WHERE type = ? AND (language = ? OR language IS NULL) ORDER BY name", (type, language))
        else:
            cursor.execute("SELECT id, name, parent_id, language FROM collections WHERE type = ? ORDER BY name", (type,))
        cols = []
        for row in cursor.fetchall():
            cols.append({"id": row[0], "name": row[1], "parent_id": row[2], "language": row[3]})
        return cols

    def delete_collection(self, collection_id: int):
        """Delete a collection. Children collections and items will be 'uncategorized' (null)."""
        cursor = self.conn.cursor()
        # Set parent_id to NULL for children
        cursor.execute("UPDATE collections SET parent_id = NULL WHERE parent_id = ?", (collection_id,))
        # The ON DELETE SET NULL on other tables handles items
        cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
        self.conn.commit()

    def assign_to_collection(self, item_type: str, item_id: int, collection_id: int):
        """Assign an item (deck, word, sentence, grammar) to a collection."""
        cursor = self.conn.cursor()
        table_map = {
            'deck': 'decks',
            'word': 'imported_content',
            'sentence': 'imported_content',
            'grammar': 'grammar_book_entries'
        }
        table = table_map.get(item_type)
        if not table:
            return False
            
        cursor.execute(f"UPDATE {table} SET collection_id = ? WHERE id = ?", (collection_id, item_id))
        self.conn.commit()
        return True
    def create_deck(self, name: str, description: str = "", language: str = None) -> int:
        """Create a new deck and return its ID."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO decks (name, created_at, description, language) VALUES (?, ?, ?, ?)",
                (name, datetime.now().isoformat(), description, language)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_all_decks(self, language: str = None) -> list[dict]:
        """Get all decks with their statistics, optionally filtered by language."""
        cursor = self.conn.cursor()
        if language:
            cursor.execute("SELECT id, name, description, created_at, collection_id, language FROM decks WHERE language = ? OR language IS NULL ORDER BY name", (language,))
        else:
            cursor.execute("SELECT id, name, description, created_at, collection_id, language FROM decks ORDER BY name")
        decks = []
        for row in cursor.fetchall():
            deck_id = row[0]
            # Count total cards
            cursor.execute("SELECT COUNT(*) FROM flashcards WHERE deck_id = ?", (deck_id,))
            total = cursor.fetchone()[0]
            # Count due cards (simplified - cards with no review or old reviews)
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM flashcards WHERE deck_id = ? AND (last_reviewed IS NULL OR last_reviewed = '')",
                    (deck_id,)
                )
                due_never = cursor.fetchone()[0]
                
                cursor.execute(
                    """SELECT COUNT(*) FROM flashcards 
                       WHERE deck_id = ? 
                       AND last_reviewed IS NOT NULL 
                       AND last_reviewed != '' 
                       AND (strftime('%s', 'now') - strftime('%s', last_reviewed)) / 86400 >= interval""",
                    (deck_id,)
                )
                due_review = cursor.fetchone()[0]
                due = due_never + due_review
            except Exception as e:
                # print(f"Error counting due cards: {e}")
                due = 0
            
            decks.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "collection_id": row[4],
                "language": row[5],
                "total_cards": total,
                "due_cards": due
            })
        return decks

    def delete_deck(self, deck_id: int) -> bool:
        """Delete a deck and all its flashcards."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_flashcard(self, deck_id: int, question: str, answer: str) -> Flashcard:
        """Add a flashcard to a deck."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO flashcards (deck_id, question, answer) VALUES (?, ?, ?)",
            (deck_id, question, answer)
        )
        flashcard_id = cursor.lastrowid
        self.conn.commit()
        return self.get_flashcard(flashcard_id)

    def get_flashcard(self, flashcard_id: int) -> Flashcard:
        """Get a specific flashcard."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, question, answer, last_reviewed, easiness, interval, repetitions, total_reviews, correct_reviews FROM flashcards WHERE id = ?",
            (flashcard_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        flashcard = Flashcard(row[1], row[2], card_id=row[0])
        flashcard.last_reviewed = datetime.fromisoformat(row[3]) if row[3] else None
        flashcard.easiness = row[4]
        flashcard.interval = row[5]
        flashcard.repetitions = row[6]
        flashcard.total_reviews = row[7]
        flashcard.correct_reviews = row[8]
        return flashcard

    def get_all_flashcards(self, deck_id: int) -> list[Flashcard]:
        """Get all flashcards in a deck."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, question, answer, last_reviewed, easiness, interval, repetitions, total_reviews, correct_reviews FROM flashcards WHERE deck_id = ? ORDER BY id",
            (deck_id,)
        )
        flashcards = []
        for row in cursor.fetchall():
            flashcard = Flashcard(row[1], row[2], card_id=row[0])
            flashcard.last_reviewed = datetime.fromisoformat(row[3]) if row[3] else None
            flashcard.easiness = row[4]
            flashcard.interval = row[5]
            flashcard.repetitions = row[6]
            flashcard.total_reviews = row[7]
            flashcard.correct_reviews = row[8]
            flashcards.append(flashcard)
        return flashcards

    def get_due_flashcards(self, deck_id: int) -> list[Flashcard]:
        """Get flashcards due for review in a deck."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, question, answer, last_reviewed, easiness, interval, repetitions, total_reviews, correct_reviews FROM flashcards
            WHERE deck_id = ? AND (last_reviewed IS NULL OR
                  (strftime('%s', 'now') - strftime('%s', last_reviewed)) / 86400 >= interval)
            ORDER BY last_reviewed ASC, id ASC
        """, (deck_id,))
        
        flashcards = []
        for row in cursor.fetchall():
            flashcard = Flashcard(row[1], row[2], card_id=row[0])
            flashcard.last_reviewed = datetime.fromisoformat(row[3]) if row[3] else None
            flashcard.easiness = row[4]
            flashcard.interval = row[5]
            flashcard.repetitions = row[6]
            flashcard.total_reviews = row[7]
            flashcard.correct_reviews = row[8]
            flashcards.append(flashcard)
        return flashcards

    def update_flashcard(self, flashcard):
        # Update a flashcard's content and stats
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE flashcards SET question = ?, answer = ?, last_reviewed = ?, easiness = ?, interval = ?, repetitions = ?, total_reviews = ?, correct_reviews = ? WHERE id = ?",
            (
                flashcard.question,
                flashcard.answer,
                flashcard.last_reviewed.isoformat() if flashcard.last_reviewed else None,
                flashcard.easiness,
                flashcard.interval,
                flashcard.repetitions,
                flashcard.total_reviews,
                flashcard.correct_reviews,
                flashcard.id
            )
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_flashcard(self, flashcard_id: int) -> bool:
        """Delete a flashcard."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM flashcards WHERE id = ?", (flashcard_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def find_flashcard_by_question(self, question: str) -> list[dict]:
        """Find flashcards by question text across all decks (case-insensitive)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT f.id, f.question, f.answer, d.name as deck_name
            FROM flashcards f
            JOIN decks d ON f.deck_id = d.id
            WHERE LOWER(f.question) = LOWER(?)
        """, (question.strip(),))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "deck_name": row[3]
            })
        return results

    def get_deck_statistics(self, deck_id: int) -> dict:
        """Get statistics for a deck."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM flashcards WHERE deck_id = ?", (deck_id,))
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(correct_reviews), SUM(total_reviews) FROM flashcards WHERE deck_id = ?", (deck_id,))
        row = cursor.fetchone()
        correct = row[0] or 0
        total_reviews = row[1] or 0
        
        cursor.execute(
            "SELECT COUNT(*) FROM flashcards WHERE deck_id = ? AND (last_reviewed IS NULL OR (strftime('%s', 'now') - strftime('%s', last_reviewed)) / 86400 >= interval)",
            (deck_id,)
        )
        due = cursor.fetchone()[0]
        
        return {
            "total_cards": total,
            "due_cards": due,
            "total_reviews": total_reviews,
            "correct_reviews": correct,
            "overall_accuracy": (correct / total_reviews * 100) if total_reviews > 0 else 0.0
        }

    # ===== IMPORTED CONTENT METHODS =====

    def add_imported_content(self, content_type: str, content: str, url: str, 
                           title: str = "", context: str = "", language: str = "", 
                           tags: str = "") -> int:
        """Add imported content from browser extension."""
        print(f'\n[DB] add_imported_content called: type={content_type}, content={content[:50]}...', flush=True)
        cursor = self.conn.cursor()
        try:
            print(f'[DB] Executing INSERT...', flush=True)
            cursor.execute("""
                INSERT INTO imported_content 
                (content_type, content, context, title, url, language, created_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (content_type, content, context, title, url, language, 
                  datetime.now().isoformat(), tags))
            print(f'[DB] INSERT executed', flush=True)
            self.conn.commit()
            print(f'[DB] COMMIT successful', flush=True)
            row_id = cursor.lastrowid
            print(f'[DB] Returned row ID: {row_id}', flush=True)
            return row_id
        except Exception as e:
            print(f'[DB] ERROR in add_imported_content: {str(e)}', flush=True)
            import traceback
            traceback.print_exc()
            raise

    def get_imported_content(self, limit: int = 50, offset: int = 0, language: str = None) -> list[dict]:
        """Get imported content for review, optionally filtered by language."""
        cursor = self.conn.cursor()
        if language:
            cursor.execute("""
                SELECT id, content_type, content, context, title, url, language, created_at, processed, tags
                FROM imported_content 
                WHERE language = ? OR language IS NULL
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (language, limit, offset))
        else:
            cursor.execute("""
                SELECT id, content_type, content, context, title, url, language, created_at, processed, tags
                FROM imported_content 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "content_type": row[1],
                "content": row[2],
                "context": row[3],
                "title": row[4],
                "url": row[5],
                "language": row[6],
                "created_at": row[7],
                "processed": bool(row[8]),
                "tags": row[9] or ""
            })
        return results

    def get_imported_content_by_type(self, content_type: str, language: str = None) -> list[dict]:
        """Get imported content by type (word, sentence, phrase), optionally filtered by language."""
        cursor = self.conn.cursor()
        if language:
            cursor.execute("""
                SELECT id, content_type, content, context, title, url, language, created_at, processed, tags
                FROM imported_content 
                WHERE content_type = ? AND (language = ? OR language IS NULL)
                ORDER BY created_at DESC
            """, (content_type, language))
        else:
            cursor.execute("""
                SELECT id, content_type, content, context, title, url, language, created_at, processed, tags
                FROM imported_content 
                WHERE content_type = ?
                ORDER BY created_at DESC
            """, (content_type,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "content_type": row[1],
                "content": row[2],
                "context": row[3],
                "title": row[4],
                "url": row[5],
                "language": row[6],
                "created_at": row[7],
                "processed": bool(row[8]),
                "tags": row[9] or ""
            })
        return results

    def mark_content_processed(self, content_id: int) -> bool:
        """Mark imported content as processed (converted to flashcards)."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE imported_content SET processed = 1 WHERE id = ?", (content_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_imported_content(self, content_id: int) -> bool:
        """Delete imported content."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM imported_content WHERE id = ?", (content_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_imported_content_stats(self, language: str = None) -> dict:
        """Get statistics about imported content, optionally filtered by language."""
        cursor = self.conn.cursor()
        
        if language:
            # Total imported items
            cursor.execute("SELECT COUNT(*) FROM imported_content WHERE language = ? OR language IS NULL", (language,))
            total = cursor.fetchone()[0]
            
            # By type
            cursor.execute("SELECT content_type, COUNT(*) FROM imported_content WHERE language = ? OR language IS NULL GROUP BY content_type", (language,))
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Processed vs unprocessed
            cursor.execute("SELECT processed, COUNT(*) FROM imported_content WHERE language = ? OR language IS NULL GROUP BY processed", (language,))
            processed_counts = {bool(row[0]): row[1] for row in cursor.fetchall()}
        else:
            # Total imported items
            cursor.execute("SELECT COUNT(*) FROM imported_content")
            total = cursor.fetchone()[0]
            
            # By type
            cursor.execute("SELECT content_type, COUNT(*) FROM imported_content GROUP BY content_type")
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Processed vs unprocessed
            cursor.execute("SELECT processed, COUNT(*) FROM imported_content GROUP BY processed")
            processed_counts = {bool(row[0]): row[1] for row in cursor.fetchall()}
        
        return {
            "total_imported": total,
            "by_type": type_counts,
            "processed": processed_counts.get(True, 0),
            "unprocessed": processed_counts.get(False, 0)
        }
    
    # ===== GRAMMAR FOLLOW-UP METHODS =====
    
    def add_grammar_followup(self, sentence_explanation_id: int, question: str, 
                            answer: str, context: str = "") -> int:
        """Add a grammar follow-up question and answer."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO grammar_followups 
            (sentence_explanation_id, question, answer, context, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (sentence_explanation_id, question, answer, context, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_grammar_followups(self, sentence_explanation_id: int) -> list[dict]:
        """Get all grammar follow-ups for a sentence explanation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, question, answer, context, created_at
            FROM grammar_followups
            WHERE sentence_explanation_id = ?
            ORDER BY created_at ASC
        """, (sentence_explanation_id,))
        
        followups = []
        for row in cursor.fetchall():
            followups.append({
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "context": row[3],
                "created_at": row[4]
            })
        return followups
    
    def delete_grammar_followup(self, followup_id: int) -> bool:
        """Delete a specific grammar follow-up."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM grammar_followups WHERE id = ?", (followup_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def clear_grammar_followups(self, sentence_explanation_id: int) -> bool:
        """Clear all follow-ups for a sentence explanation."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM grammar_followups WHERE sentence_explanation_id = ?", 
                      (sentence_explanation_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ===== GRAMMAR BOOK METHODS =====

    def add_grammar_entry(self, title: str, content: str, language: str = "", tags: str = "") -> int:
        """Add a new entry to the grammar book."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO grammar_book_entries 
            (title, content, language, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, content, language, tags, datetime.now().isoformat(), datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid

    def get_grammar_entries(self, search_query: str = "") -> list[dict]:
        """Get all grammar book entries, optionally filtered by search query."""
        cursor = self.conn.cursor()
        if search_query:
            query = """
                SELECT id, title, content, language, tags, created_at, updated_at, collection_id
                FROM grammar_book_entries
                WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                ORDER BY updated_at DESC
            """
            search_pattern = f"%{search_query}%"
            cursor.execute(query, (search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute("""
                SELECT id, title, content, language, tags, created_at, updated_at, collection_id
                FROM grammar_book_entries
                ORDER BY updated_at DESC
            """)
        
        entries = []
        for row in cursor.fetchall():
            entries.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "language": row[3],
                "tags": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "collection_id": row[7]
            })
        return entries

    def get_grammar_entry(self, entry_id: int) -> dict:
        """Get a specific grammar book entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, content, language, tags, created_at, updated_at, collection_id
            FROM grammar_book_entries
            WHERE id = ?
        """, (entry_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "language": row[3],
                "tags": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "collection_id": row[7]
            }
        return None

    def update_grammar_entry(self, entry_id: int, title: str, content: str, language: str, tags: str) -> bool:
        """Update an existing grammar book entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE grammar_book_entries
            SET title = ?, content = ?, language = ?, tags = ?, updated_at = ?
            WHERE id = ?
        """, (title, content, language, tags, datetime.now().isoformat(), entry_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_grammar_entry(self, entry_id: int) -> bool:
        """Delete a grammar book entry."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM grammar_book_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ===== WRITING SESSIONS METHODS =====

    def add_writing_session(self, topic: str, user_writing: str, feedback: str, grade: str, study_language: str, analysis: str = None) -> int:
        """Add a new writing session record."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO writing_sessions (topic, user_writing, feedback, grade, study_language, analysis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (topic, user_writing, feedback, grade, study_language, analysis, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid

    def get_writing_sessions(self, language: str = None) -> List[Dict]:
        """Get all writing sessions, optionally filtered by language."""
        cursor = self.conn.cursor()
        if language:
            cursor.execute("""
                SELECT id, topic, user_writing, feedback, grade, study_language, analysis, created_at 
                FROM writing_sessions 
                WHERE study_language = ? 
                ORDER BY created_at DESC
            """, (language,))
        else:
            cursor.execute("""
                SELECT id, topic, user_writing, feedback, grade, study_language, analysis, created_at 
                FROM writing_sessions 
                ORDER BY created_at DESC
            """)
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'topic': row[1],
                'user_writing': row[2],
                'feedback': row[3],
                'grade': row[4],
                'study_language': row[5],
                'analysis': row[6],
                'created_at': row[7]
            })
        return sessions

    def delete_writing_session(self, session_id: int) -> bool:
        """Delete a writing session."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM writing_sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ===== CHAT METHODS =====

    def create_chat_session(self, topic: str, study_language: str) -> int:
        """Create a new chat session."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO chat_sessions (cur_topic, study_language, created_at, last_updated)
            VALUES (?, ?, ?, ?)
        """, (topic, study_language, now, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_chat_sessions(self, study_language: Optional[str] = None) -> List[Dict]:
        """Get list of chat sessions."""
        cursor = self.conn.cursor()
        if study_language:
            cursor.execute("SELECT * FROM chat_sessions WHERE study_language = ? ORDER BY last_updated DESC", (study_language,))
        else:
            cursor.execute("SELECT * FROM chat_sessions ORDER BY last_updated DESC")
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def add_chat_message(self, session_id: int, role: str, content: str, analysis: Optional[str] = None) -> int:
        """Add a message to a chat session."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content, analysis, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, role, content, analysis, now))
        
        # Update session timestamp
        cursor.execute("UPDATE chat_sessions SET last_updated = ? WHERE id = ?", (now, session_id))
        
        self.conn.commit()
        return cursor.lastrowid

    def get_chat_messages(self, session_id: int) -> List[Dict]:
        """Get all messages for a session."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def delete_chat_session(self, session_id: int) -> bool:
        """Delete a chat session."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ===== SETTINGS METHODS =====

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value by key."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT setting_value FROM study_settings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def update_setting(self, key: str, value: str):
        """Update or insert a setting."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO study_settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """, (key, value))
        self.conn.commit()

    def delete_setting(self, key: str):
        """Delete a setting."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM study_settings WHERE setting_key = ?", (key,))
        self.conn.commit()

    def clear_settings_pattern(self, pattern: str):
        """Delete settings matching a LIKE pattern."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM study_settings WHERE setting_key LIKE ?", (pattern,))
        self.conn.commit()

    def close(self):
        self.conn.close()