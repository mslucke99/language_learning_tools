import sqlite3
from flashcard import Flashcard
from datetime import datetime

class FlashcardDatabase:
    def __init__(self, db_name="flashcards.db"):
        # check_same_thread=False allows the connection to be used across Flask request threads
        # This is safe for this application since we're not doing concurrent writes
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Create decks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                description TEXT
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
        self.conn.commit()

    def create_deck(self, name: str, description: str = "") -> int:
        """Create a new deck and return its ID."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO decks (name, created_at, description) VALUES (?, ?, ?)",
                (name, datetime.now().isoformat(), description)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_all_decks(self) -> list[dict]:
        """Get all decks with their statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, created_at FROM decks ORDER BY name")
        decks = []
        for row in cursor.fetchall():
            deck_id = row[0]
            # Count total cards
            cursor.execute("SELECT COUNT(*) FROM flashcards WHERE deck_id = ?", (deck_id,))
            total = cursor.fetchone()[0]
            # Count due cards (simplified - cards with no review or old reviews)
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM flashcards WHERE deck_id = ? AND last_reviewed IS NULL",
                    (deck_id,)
                )
                due = cursor.fetchone()[0]
            except:
                due = 0
            
            decks.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
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

    def update_flashcard(self, flashcard: Flashcard) -> bool:
        """Update a flashcard's stats."""
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE flashcards 
               SET last_reviewed = ?, easiness = ?, interval = ?, repetitions = ?, 
                   total_reviews = ?, correct_reviews = ?
               WHERE id = ?""",
            (
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

    def close(self):
        self.conn.close()