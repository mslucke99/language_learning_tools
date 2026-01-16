"""
Quiz Manager - Handles quiz generation and scoring
"""

import random
import json
from typing import List, Dict, Tuple, Optional
from src.core.database import FlashcardDatabase
from src.services.llm_service import OllamaClient
from src.services.prompts import EXAM_PROMPTS
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

    # --- EXAM PRACTICE MODE ---

    def create_exam_attempt(self, exam_name: str, level: str, section: str, total: int) -> int:
        """Create a new exam attempt record."""
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO exam_attempts (exam_name, level, section, score, total_questions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (exam_name, level, section, 0, total, now))
        attempt_id = cursor.lastrowid
        self.db.conn.commit()
        return attempt_id

    def generate_exam_questions(self, attempt_id: int, exam_name: str, level: str, section: str, count: int, 
                               study_lang: str, native_lang: str) -> bool:
        """Generate exam questions using AI and save to database."""
        if not self.ollama_client or not self.ollama_client.is_available():
            return False

        template = EXAM_PROMPTS['generate_question']['template']
        
        for i in range(count):
            try:
                # We ask for one question at a time to ensure better quality/parsing
                prompt = template.format(
                    exam_name=exam_name,
                    level=level,
                    section=section,
                    native_language=native_lang,
                    study_language=study_lang,
                    focus_area=f"Question {i+1} of {count}"
                )
                
                response = self.ollama_client.generate_response(prompt, timeout=self.timeout)
                if not response: continue
                
                # Cleanup potential markdown
                clean_json = response.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].strip()
                
                data = json.loads(clean_json)
                
                # Save to database
                cursor = self.db.conn.cursor()
                # Determine which letter the correct answer corresponds to
                options = data.get('options', [])
                correct_str = data.get('correct_answer', '')
                
                letters = ['A', 'B', 'C', 'D']
                correct_letter = 'A'
                for idx, opt in enumerate(options[:4]):
                    if opt == correct_str:
                        correct_letter = letters[idx]
                        break
                
                cursor.execute("""
                    INSERT INTO exam_questions (attempt_id, question_text, correct_answer, 
                                              choice_a, choice_b, choice_c, choice_d, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    attempt_id, 
                    data.get('question', ''), 
                    correct_letter,
                    options[0] if len(options) > 0 else '',
                    options[1] if len(options) > 1 else '',
                    options[2] if len(options) > 2 else '',
                    options[3] if len(options) > 3 else '',
                    data.get('explanation', '')
                ))
                self.db.conn.commit()
                
            except Exception as e:
                print(f"Error generating exam question {i}: {e}")
                continue
        
        return True

    def get_exam_questions(self, attempt_id: int) -> List[Dict]:
        """Fetch all questions for a specific exam attempt."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM exam_questions WHERE attempt_id = ? ORDER BY id", (attempt_id,))
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def submit_exam_answer(self, question_id: int, user_answer_letter: str) -> bool:
        """Submit and verify an exam answer."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT correct_answer FROM exam_questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        if not row: return False
        
        is_correct = 1 if user_answer_letter == row[0] else 0
        cursor.execute("UPDATE exam_questions SET user_answer = ?, is_correct = ? WHERE id = ?", 
                      (user_answer_letter, is_correct, question_id))
        self.db.conn.commit()
        return bool(is_correct)

    def finalize_exam_attempt(self, attempt_id: int) -> Dict:
        """Calculate and save final exam score."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM exam_questions WHERE attempt_id = ? AND is_correct = 1", (attempt_id,))
        correct = cursor.fetchone()[0]
        
        cursor.execute("SELECT total_questions FROM exam_attempts WHERE id = ?", (attempt_id,))
        total = cursor.fetchone()[0]
        
        score = int((correct / total) * 100) if total > 0 else 0
        cursor.execute("UPDATE exam_attempts SET score = ? WHERE id = ?", (score, attempt_id))
        self.db.conn.commit()
        
        return {'score': score, 'correct': correct, 'total': total}
