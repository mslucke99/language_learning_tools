"""
Quiz Manager - Handles quiz generation and scoring
"""

import random
import json
from typing import List, Dict, Tuple, Optional
from database import FlashcardDatabase
from ollama_integration import OllamaClient
from datetime import datetime


class QuizManager:
    """Manages quiz generation and scoring."""
    
    def __init__(self, db: FlashcardDatabase, ollama_client: Optional[OllamaClient] = None, timeout: int = 30):
        self.db = db
        self.ollama_client = ollama_client
        self.timeout = timeout
        
    def generate_quiz(self, source_type: str, source_id: int, count: int, difficulty: str) -> int:
        """
        Generate a new quiz session.
        
        Args:
            source_type: 'deck', 'vocab', or 'grammar'
            source_id: ID of the deck or collection
            count: Number of questions
            difficulty: 'easy', 'medium', or 'hard'
            
        Returns:
            session_id
        """
        # Fetch items based on source
        items = self._fetch_quiz_items(source_type, source_id)
        
        if not items:
            return -1
            
        # Randomly select items
        selected = random.sample(items, min(count, len(items)))
        
        # Create session
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO quiz_sessions (source_type, source_id, question_count, difficulty, score, total_questions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source_type, source_id, len(selected), difficulty, 0, len(selected), now))
        session_id = cursor.lastrowid
        self.db.conn.commit()
        
        # Generate questions
        for item in selected:
            self._create_question(session_id, item, source_type, difficulty)
            
        return session_id
        
    def _fetch_quiz_items(self, source_type: str, source_id: int) -> List[Dict]:
        """Fetch items to quiz from."""
        cursor = self.db.conn.cursor()
        
        if source_type == 'deck':
            cursor.execute("SELECT question, answer FROM flashcards WHERE deck_id = ?", (source_id,))
            return [{'question': row[0], 'answer': row[1], 'type': 'flashcard'} for row in cursor.fetchall()]
            
        elif source_type == 'vocab':
            # Get words from collection
            cursor.execute("""
                SELECT ic.content, wd.definition 
                FROM imported_content ic
                JOIN word_definitions wd ON ic.id = wd.imported_content_id
                WHERE ic.collection_id = ? AND ic.content_type = 'word'
            """, (source_id,))
            return [{'question': f"What does '{row[0]}' mean?", 'answer': row[1], 'type': 'vocab'} for row in cursor.fetchall()]
            
        elif source_type == 'grammar':
            # Get grammar patterns from collection
            cursor.execute("""
                SELECT title, content 
                FROM grammar_book_entries
                WHERE collection_id = ?
            """, (source_id,))
            return [{'question': f"Explain: {row[0]}", 'answer': row[1], 'type': 'grammar'} for row in cursor.fetchall()]
            
        return []
        
    def _create_question(self, session_id: int, item: Dict, source_type: str, difficulty: str):
        """Create a multiple choice question."""
        question_text = item['question']
        correct_answer = item['answer']
        
        # Generate distractors
        distractors = self._generate_distractors(correct_answer, difficulty, item['type'])
        
        # Shuffle choices
        all_choices = [correct_answer] + distractors
        random.shuffle(all_choices)
        
        # Assign to A, B, C, D
        choices = {'A': all_choices[0], 'B': all_choices[1], 'C': all_choices[2], 'D': all_choices[3]}
        
        # Find correct letter
        correct_letter = [k for k, v in choices.items() if v == correct_answer][0]
        
        # Save question
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO quiz_questions (session_id, question_text, correct_answer, choice_a, choice_b, choice_c, choice_d, user_answer, is_correct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, question_text, correct_letter, choices['A'], choices['B'], choices['C'], choices['D'], None, None))
        self.db.conn.commit()
        
    def _generate_distractors(self, correct_answer: str, difficulty: str, item_type: str) -> List[str]:
        """Generate plausible wrong answers using AI or fallback."""
        if self.ollama_client and self.ollama_client.is_available():
            try:
                prompt = f"""Generate 3 plausible but incorrect answers for this question.
Correct answer: {correct_answer}
Difficulty: {difficulty}
Type: {item_type}

Provide only the 3 wrong answers, one per line. Make them believable distractors."""
                
                response = self.ollama_client.generate_response(prompt, timeout=self.timeout)
                if response:
                    distractors = [line.strip() for line in response.split('\n') if line.strip()][:3]
                    if len(distractors) == 3:
                        return distractors
            except:
                pass
                
        # Fallback: generic distractors
        return [
            f"Option A (incorrect)",
            f"Option B (incorrect)",  
            f"Option C (incorrect)"
        ]
        
    def get_quiz_questions(self, session_id: int) -> List[Dict]:
        """Get all questions for a quiz session."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM quiz_questions WHERE session_id = ? ORDER BY id", (session_id,))
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
        
    def submit_answer(self, question_id: int, user_answer: str) -> bool:
        """Submit an answer for a question."""
        cursor = self.db.conn.cursor()
        
        # Get correct answer
        cursor.execute("SELECT correct_answer FROM quiz_questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        correct = row[0]
        is_correct = 1 if user_answer == correct else 0
        
        # Update question
        cursor.execute("""
            UPDATE quiz_questions 
            SET user_answer = ?, is_correct = ?
            WHERE id = ?
        """, (user_answer, is_correct, question_id))
        self.db.conn.commit()
        
        return is_correct == 1
        
    def calculate_score(self, session_id: int) -> Dict:
        """Calculate final score for a session."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quiz_questions WHERE session_id = ? AND is_correct = 1", (session_id,))
        correct_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT total_questions FROM quiz_sessions WHERE id = ?", (session_id,))
        total = cursor.fetchone()[0]
        
        score = int((correct_count / total) * 100) if total > 0 else 0
        
        # Update session
        cursor.execute("UPDATE quiz_sessions SET score = ? WHERE id = ?", (score, session_id))
        self.db.conn.commit()
        
        return {
            'score': score,
            'correct': correct_count,
            'total': total
        }
