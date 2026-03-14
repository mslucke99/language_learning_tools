"""
Annotations and Comprehension Questions for Immersive Reading Mode.

Handles:
- Comprehension question generation
- Answer recording
- Annotation storage (highlights, notes, bookmarks)
- Bookmark navigation
"""

import time
from typing import Dict, List, Optional
from src.core.database import FlashcardDatabase
from src.features.reader.llm_agent import LLMService


class AnnotationManager:
    """
    Manages annotations and comprehension questions for reading sessions.
    
    Handles:
    - Creating and storing annotations (highlights, notes, bookmarks)
    - Generating comprehension questions
    - Recording user answers
    - Bookmark navigation
    
    Requirements:
        - 11.1: Generate comprehension questions
        - 11.2: Create questions testing main idea, details, inference
        - 11.3: Provide four answer options with one correct answer
        - 11.4: Record question answers
        - 12.1: Save highlights with positions
        - 12.2: Support annotation types
        - 12.3: Store notes with highlights
        - 12.4: Display saved annotations on reopen
        - 12.5: Allow annotation deletion
        - 17.1: Bookmark creation
        - 17.2: Display bookmark indicators
        - 17.3: Provide bookmark list
        - 17.4: Navigate to bookmarked positions
        - 17.5: Delete bookmarks
    """
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize the AnnotationManager.
        
        Args:
            db: FlashcardDatabase instance for data persistence
        """
        self.db = db
    
    def generate_comprehension_question(
        self,
        session_id: int,
        paragraph_index: int,
        language: str
    ) -> Optional[Dict]:
        """
        Generate a comprehension question for a paragraph.
        
        Uses LLMService to generate multiple-choice questions testing
        main idea, specific details, or inference.
        
        Args:
            session_id: Reading session ID
            paragraph_index: Index of the paragraph to generate question for
            language: Target language code
            
        Returns:
            Dictionary with question data:
            {
                'question': str,
                'choice_a': str,
                'choice_b': str,
                'choice_c': str,
                'choice_d': str,
                'correct_answer': str,  # 'A', 'B', 'C', or 'D'
                'question_type': str  # 'main_idea', 'detail', 'inference'
            }
            or None if generation failed
            
        Requirements:
            - 11.1: Generate comprehension questions
            - 11.2: Test main idea, details, inference
            - 11.3: Four answer options with one correct
        """
        cursor = self.db.conn.cursor()
        
        # Get the paragraph content
        cursor.execute("""
            SELECT content FROM reading_sessions WHERE id = ?
        """, (session_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        content = row[0]
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        if paragraph_index >= len(paragraphs):
            return None
        
        paragraph = paragraphs[paragraph_index]
        
        # Use LLMService to generate question
        llm = LLMService()
        
        prompt = f"""Generate a multiple-choice comprehension question for the following paragraph in {language}.

Paragraph:
{paragraph}

Requirements:
- Create ONE question testing main idea, specific detail, or inference
- Provide FOUR answer options (A, B, C, D)
- Mark the correct answer clearly

Format your response as:
QUESTION: [your question]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
CORRECT: [A/B/C/D]
TYPE: [main_idea/detail/inference]"""
        
        try:
            response = llm.generate_response(prompt, timeout=60)
            
            # Parse the response
            question_data = self._parse_comprehension_response(response)
            
            if question_data:
                # Store in database
                question_data['session_id'] = session_id
                question_data['paragraph_index'] = paragraph_index
                self._store_comprehension_question(question_data)
                
                return question_data
            
            return None
            
        except Exception as e:
            print(f"Error generating comprehension question: {e}")
            return None
    
    def _parse_comprehension_response(self, response: str) -> Optional[Dict]:
        """
        Parse LLM response for comprehension question.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            Parsed question data or None if parsing failed
        """
        try:
            question_data = {}
            
            # Parse question
            if 'QUESTION:' in response:
                question_part = response.split('QUESTION:')[1].split('\n')[0].strip()
                question_data['question'] = question_part
            
            # Parse choices
            for choice in ['A', 'B', 'C', 'D']:
                key = f'{choice})'
                if key in response:
                    choice_text = response.split(key)[1].split('\n')[0].strip()
                    question_data[f'choice_{choice.lower()}'] = choice_text
            
            # Parse correct answer
            if 'CORRECT:' in response:
                correct = response.split('CORRECT:')[1].split('\n')[0].strip().upper()
                question_data['correct_answer'] = correct
            
            # Parse question type
            if 'TYPE:' in response:
                qtype = response.split('TYPE:')[1].split('\n')[0].strip().lower()
                question_data['question_type'] = qtype
            
            # Validate required fields
            required = ['question', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'correct_answer']
            if all(field in question_data for field in required):
                return question_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing comprehension response: {e}")
            return None
    
    def _store_comprehension_question(self, question_data: Dict) -> int:
        """
        Store comprehension question in database.
        
        Args:
            question_data: Question data dictionary
            
        Returns:
            ID of stored question
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, paragraph_index, question, question_type,
             choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_data['session_id'],
            question_data['paragraph_index'],
            question_data['question'],
            question_data.get('question_type', 'main_idea'),
            question_data['choice_a'],
            question_data['choice_b'],
            question_data['choice_c'],
            question_data['choice_d'],
            question_data['correct_answer']
        ))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def record_answer(
        self,
        session_id: int,
        question_id: int,
        user_answer: str,
        correct_answer: str
    ) -> int:
        """
        Record user's answer to a comprehension question.
        
        Args:
            session_id: Reading session ID
            question_id: ID of the comprehension question
            user_answer: User's answer ('A', 'B', 'C', or 'D')
            correct_answer: Correct answer ('A', 'B', 'C', or 'D')
            
        Returns:
            ID of the answer record
            
        Requirements:
            - 11.4: Record question answers
        """
        cursor = self.db.conn.cursor()
        
        # Calculate correctness
        is_correct = user_answer.upper() == correct_answer.upper()
        
        # Update the existing comprehension question record with user's answer
        cursor.execute("""
            UPDATE reading_comprehension
            SET user_answer = ?, is_correct = ?, timestamp = CURRENT_TIMESTAMP
            WHERE id = ? AND session_id = ?
        """, (user_answer, is_correct, question_id, session_id))
        
        self.db.conn.commit()
        return question_id
    
    def create_annotation(
        self,
        session_id: int,
        start_position: int,
        end_position: int,
        text: str,
        annotation_type: str,
        note: Optional[str] = None
    ) -> int:
        """
        Create an annotation (highlight, note, or bookmark).
        
        Args:
            session_id: Reading session ID
            start_position: Start character position
            end_position: End character position
            text: Highlighted text
            annotation_type: Type ('highlight', 'note', or 'bookmark')
            note: Optional note text
            
        Returns:
            ID of created annotation
            
        Requirements:
            - 12.1: Save highlights with positions
            - 12.2: Support annotation types
            - 12.3: Store notes with highlights
            - 17.1: Bookmark creation
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_annotations
            (session_id, user_id, start_position, end_position,
             highlighted_text, annotation_type, note_text)
            VALUES (?, 1, ?, ?, ?, ?, ?)
        """, (
            session_id,
            start_position,
            end_position,
            text,
            annotation_type,
            note
        ))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def get_annotations(self, session_id: int) -> List[Dict]:
        """
        Get all annotations for a session.
        
        Args:
            session_id: Reading session ID
            
        Returns:
            List of annotation dictionaries
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id, start_position, end_position, highlighted_text,
                   annotation_type, note_text, created_at
            FROM reading_annotations
            WHERE session_id = ?
            ORDER BY start_position
        """, (session_id,))
        
        rows = cursor.fetchall()
        
        return [
            {
                'id': row[0],
                'start_position': row[1],
                'end_position': row[2],
                'highlighted_text': row[3],
                'annotation_type': row[4],
                'note_text': row[5],
                'created_at': row[6]
            }
            for row in rows
        ]
    
    def delete_annotation(self, annotation_id: int) -> bool:
        """
        Delete an annotation.
        
        Args:
            annotation_id: ID of annotation to delete
            
        Returns:
            True if deleted, False if not found
            
        Requirements:
            - 12.5: Allow annotation deletion
            - 17.5: Delete bookmarks
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            DELETE FROM reading_annotations WHERE id = ?
        """, (annotation_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def get_bookmarks(self, session_id: int) -> List[Dict]:
        """
        Get all bookmarks for a session.
        
        Filters annotations where annotation_type='bookmark'.
        
        Args:
            session_id: Reading session ID
            
        Returns:
            List of bookmark dictionaries with position and note
            
        Requirements:
            - 17.2: Display bookmark indicators
            - 17.3: Provide bookmark list
            - 17.4: Navigate to bookmarked positions
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id, start_position, note_text
            FROM reading_annotations
            WHERE session_id = ? AND annotation_type = 'bookmark'
            ORDER BY start_position
        """, (session_id,))
        
        rows = cursor.fetchall()
        
        return [
            {
                'id': row[0],
                'position': row[1],
                'note': row[2]
            }
            for row in rows
        ]
    
    def get_annotation_by_id(self, annotation_id: int) -> Optional[Dict]:
        """
        Get a specific annotation by ID.
        
        Args:
            annotation_id: ID of annotation
            
        Returns:
            Annotation dictionary or None if not found
        """
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id, session_id, start_position, end_position,
                   highlighted_text, annotation_type, note_text, created_at
            FROM reading_annotations
            WHERE id = ?
        """, (annotation_id,))
        
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'session_id': row[1],
            'start_position': row[2],
            'end_position': row[3],
            'highlighted_text': row[4],
            'annotation_type': row[5],
            'note_text': row[6],
            'created_at': row[7]
        }
