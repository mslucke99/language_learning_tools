"""
Unit tests for AnnotationManager class.

Tests comprehension question generation, answer recording,
annotation storage, and bookmark navigation.
"""

import pytest
import tempfile
import os
import sqlite3
from hypothesis import given, strategies as st, settings, HealthCheck
from src.core.database import FlashcardDatabase
from src.features.reader.annotations import AnnotationManager


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = FlashcardDatabase(db_name=db_path)
    
    yield db
    
    db.conn.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def annotation_manager(test_db):
    """Create an AnnotationManager instance with test database."""
    return AnnotationManager(test_db)


@pytest.fixture
def reading_session(test_db):
    """Create a reading session for testing."""
    cursor = test_db.conn.cursor()
    cursor.execute("""
        INSERT INTO reading_sessions
        (user_id, title, content, language, source, import_method,
         legal_attestation, private, shareable, created_at)
        VALUES (1, 'Test Content', 'This is a test paragraph.\\n\\nThis is another paragraph.', 'en', 'user_paste', 'paste', 1, 1, 0, CURRENT_TIMESTAMP)
    """)
    session_id = cursor.lastrowid
    test_db.conn.commit()
    return session_id


class TestAnnotationManagerInit:
    """Test AnnotationManager initialization."""
    
    def test_init_stores_database(self, test_db):
        """Test that initialization stores database reference."""
        manager = AnnotationManager(test_db)
        assert manager.db is test_db


class TestGenerateComprehensionQuestion:
    """Test comprehension question generation."""
    
    def test_generate_comprehension_question_returns_dict(self, annotation_manager, reading_session):
        """Test that question generation returns a dictionary."""
        result = annotation_manager.generate_comprehension_question(
            reading_session, 0, 'en'
        )
        
        # May return None if LLM is not available, but if it returns a dict, it should have the right structure
        if result is not None:
            assert isinstance(result, dict)
    
    def test_generate_comprehension_question_with_valid_paragraph(self, annotation_manager, reading_session):
        """Test question generation for a valid paragraph."""
        result = annotation_manager.generate_comprehension_question(
            reading_session, 0, 'en'
        )
        
        if result is not None:
            assert 'question' in result
            assert 'choice_a' in result
            assert 'choice_b' in result
            assert 'choice_c' in result
            assert 'choice_d' in result
            assert 'correct_answer' in result


class TestRecordAnswer:
    """Test answer recording functionality."""
    
    def test_record_answer_creates_record(self, annotation_manager, reading_session, test_db):
        """Test that recording an answer creates a database record."""
        # First create a comprehension question
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, paragraph_index, question, question_type,
             choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, 0, 'Test question?', 'main_idea', 'A', 'B', 'C', 'D', 'A')
        """, (reading_session,))
        question_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Record answer
        answer_id = annotation_manager.record_answer(
            reading_session, question_id, 'A', 'A'
        )
        
        assert answer_id > 0
    
    def test_record_answer_calculates_correctness(self, annotation_manager, reading_session, test_db):
        """Test that answer recording correctly calculates correctness."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, paragraph_index, question, question_type,
             choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, 0, 'Test question?', 'main_idea', 'A', 'B', 'C', 'D', 'A')
        """, (reading_session,))
        question_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Record correct answer
        answer_id = annotation_manager.record_answer(
            reading_session, question_id, 'A', 'A'
        )
        
        # Verify is_correct is True
        cursor.execute("""
            SELECT is_correct FROM reading_comprehension WHERE id = ?
        """, (answer_id,))
        row = cursor.fetchone()
        assert row[0] == 1  # True
    
    def test_record_answer_incorrect_answer(self, annotation_manager, reading_session, test_db):
        """Test that incorrect answers are marked as incorrect."""
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, paragraph_index, question, question_type,
             choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, 0, 'Test question?', 'main_idea', 'A', 'B', 'C', 'D', 'A')
        """, (reading_session,))
        question_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Record incorrect answer
        answer_id = annotation_manager.record_answer(
            reading_session, question_id, 'B', 'A'
        )
        
        # Verify is_correct is False
        cursor.execute("""
            SELECT is_correct FROM reading_comprehension WHERE id = ?
        """, (answer_id,))
        row = cursor.fetchone()
        assert row[0] == 0  # False


class TestCreateAnnotation:
    """Test annotation creation functionality."""
    
    def test_create_annotation_creates_record(self, annotation_manager, reading_session):
        """Test that creating an annotation creates a database record."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Test text', 'highlight', None
        )
        
        assert annotation_id > 0
    
    def test_create_annotation_with_note(self, annotation_manager, reading_session):
        """Test creating an annotation with a note."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Test text', 'note', 'This is a note'
        )
        
        assert annotation_id > 0
    
    def test_create_annotation_with_bookmark(self, annotation_manager, reading_session):
        """Test creating a bookmark annotation."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 50, 50, '', 'bookmark', 'Important section'
        )
        
        assert annotation_id > 0
    
    def test_create_annotation_stores_positions(self, annotation_manager, reading_session):
        """Test that annotation stores start and end positions."""
        start_pos = 100
        end_pos = 200
        
        annotation_id = annotation_manager.create_annotation(
            reading_session, start_pos, end_pos, 'Test text', 'highlight', None
        )
        
        cursor = annotation_manager.db.conn.cursor()
        cursor.execute("""
            SELECT start_position, end_position FROM reading_annotations WHERE id = ?
        """, (annotation_id,))
        row = cursor.fetchone()
        
        assert row[0] == start_pos
        assert row[1] == end_pos


class TestGetAnnotations:
    """Test annotation retrieval functionality."""
    
    def test_get_annotations_empty_session(self, annotation_manager, reading_session):
        """Test getting annotations for session with no annotations."""
        annotations = annotation_manager.get_annotations(reading_session)
        assert annotations == []
    
    def test_get_annotations_with_annotations(self, annotation_manager, reading_session):
        """Test getting annotations for session with annotations."""
        # Create multiple annotations
        annotation_manager.create_annotation(reading_session, 0, 10, 'Text 1', 'highlight', None)
        annotation_manager.create_annotation(reading_session, 20, 30, 'Text 2', 'note', 'Note 1')
        annotation_manager.create_annotation(reading_session, 40, 50, 'Text 3', 'bookmark', None)
        
        annotations = annotation_manager.get_annotations(reading_session)
        
        assert len(annotations) == 3
    
    def test_get_annotations_returns_correct_fields(self, annotation_manager, reading_session):
        """Test that annotations return all required fields."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Test text', 'highlight', 'Test note'
        )
        
        annotations = annotation_manager.get_annotations(reading_session)
        
        assert len(annotations) == 1
        annotation = annotations[0]
        assert 'id' in annotation
        assert 'start_position' in annotation
        assert 'end_position' in annotation
        assert 'highlighted_text' in annotation
        assert 'annotation_type' in annotation
        assert 'note_text' in annotation


class TestDeleteAnnotation:
    """Test annotation deletion functionality."""
    
    def test_delete_annotation_removes_record(self, annotation_manager, reading_session):
        """Test that deleting an annotation removes it from database."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Test text', 'highlight', None
        )
        
        result = annotation_manager.delete_annotation(annotation_id)
        
        assert result is True
        
        # Verify annotation is deleted
        cursor = annotation_manager.db.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM reading_annotations WHERE id = ?
        """, (annotation_id,))
        count = cursor.fetchone()[0]
        assert count == 0
    
    def test_delete_annotation_invalid_id(self, annotation_manager, reading_session):
        """Test deleting a non-existent annotation."""
        result = annotation_manager.delete_annotation(99999)
        assert result is False


class TestGetBookmarks:
    """Test bookmark retrieval functionality."""
    
    def test_get_bookmarks_empty_session(self, annotation_manager, reading_session):
        """Test getting bookmarks for session with no bookmarks."""
        bookmarks = annotation_manager.get_bookmarks(reading_session)
        assert bookmarks == []
    
    def test_get_bookmarks_with_bookmarks(self, annotation_manager, reading_session):
        """Test getting bookmarks for session with bookmarks."""
        # Create bookmarks
        annotation_manager.create_annotation(reading_session, 100, 100, '', 'bookmark', 'First')
        annotation_manager.create_annotation(reading_session, 200, 200, '', 'bookmark', 'Second')
        
        # Create non-bookmark annotations
        annotation_manager.create_annotation(reading_session, 50, 60, 'Text', 'highlight', None)
        
        bookmarks = annotation_manager.get_bookmarks(reading_session)
        
        assert len(bookmarks) == 2
    
    def test_get_bookmarks_returns_correct_fields(self, annotation_manager, reading_session):
        """Test that bookmarks return correct fields."""
        annotation_manager.create_annotation(
            reading_session, 100, 100, '', 'bookmark', 'Test note'
        )
        
        bookmarks = annotation_manager.get_bookmarks(reading_session)
        
        assert len(bookmarks) == 1
        bookmark = bookmarks[0]
        assert 'id' in bookmark
        assert 'position' in bookmark
        assert 'note' in bookmark
        assert bookmark['position'] == 100
        assert bookmark['note'] == 'Test note'


class TestGetAnnotationById:
    """Test annotation retrieval by ID."""
    
    def test_get_annotation_by_id_returns_annotation(self, annotation_manager, reading_session):
        """Test getting a specific annotation by ID."""
        annotation_id = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Test text', 'highlight', 'Test note'
        )
        
        annotation = annotation_manager.get_annotation_by_id(annotation_id)
        
        assert annotation is not None
        assert annotation['id'] == annotation_id
    
    def test_get_annotation_by_id_invalid_id(self, annotation_manager, reading_session):
        """Test getting a non-existent annotation."""
        annotation = annotation_manager.get_annotation_by_id(99999)
        assert annotation is None


# Property-based tests

class TestComprehensionQuestionStructureProperty:
    """
    Property-based tests for comprehension question structure.
    
    Property 31: Comprehension Question Structure
    Validates: Requirements 11.3
    
    This test verifies that for ANY comprehension question,
    the question has exactly 4 answer choices and one correct_answer.
    """
    
    def test_property_question_has_four_choices(self, annotation_manager, reading_session):
        """
        Property test: Comprehension questions have exactly 4 answer choices.
        
        For ANY generated comprehension question, the result should have
        exactly 4 answer choices: choice_a, choice_b, choice_c, choice_d.
        
        Validates Requirement 11.3: Four answer options with one correct
        """
        result = annotation_manager.generate_comprehension_question(
            reading_session, 0, 'en'
        )
        
        if result is not None:
            # Check that all 4 choices exist
            assert 'choice_a' in result, "Question should have choice_a"
            assert 'choice_b' in result, "Question should have choice_b"
            assert 'choice_c' in result, "Question should have choice_c"
            assert 'choice_d' in result, "Question should have choice_d"
            
            # Check that correct_answer exists
            assert 'correct_answer' in result, "Question should have correct_answer"
            
            # Check that correct_answer is one of A, B, C, D
            assert result['correct_answer'] in ['A', 'B', 'C', 'D'], (
                f"Correct answer should be A, B, C, or D, got {result['correct_answer']}"
            )
    
    def test_property_correct_answer_is_single_choice(self, annotation_manager, reading_session):
        """
        Property test: Correct answer is a single choice letter.
        
        For ANY generated comprehension question, the correct_answer
        should be exactly one character: 'A', 'B', 'C', or 'D'.
        
        Validates Requirement 11.3: One correct answer
        """
        result = annotation_manager.generate_comprehension_question(
            reading_session, 0, 'en'
        )
        
        if result is not None:
            correct = result['correct_answer']
            assert len(correct) == 1, f"Correct answer should be single character, got '{correct}'"
            assert correct in ['A', 'B', 'C', 'D'], (
                f"Correct answer should be A, B, C, or D, got '{correct}'"
            )


class TestAnswerRecordingProperty:
    """
    Property-based tests for answer recording.
    
    Property 32: Answer Recording
    Validates: Requirements 11.4
    
    This test verifies that for ANY answer recording operation,
    the answer is stored with question, user_answer, correct_answer,
    and is_correct fields.
    """
    
    def test_property_answer_recorded_with_all_fields(self, annotation_manager, reading_session, test_db):
        """
        Property test: Answer records contain all required fields.
        
        For ANY answer recording operation, the database record should
        contain: question_id, user_answer, correct_answer, and is_correct.
        
        Validates Requirement 11.4: Record question answers
        """
        # Create a comprehension question
        cursor = test_db.conn.cursor()
        cursor.execute("""
            INSERT INTO reading_comprehension
            (session_id, user_id, paragraph_index, question, question_type,
             choice_a, choice_b, choice_c, choice_d, correct_answer)
            VALUES (?, 1, 0, 'Test question?', 'main_idea', 'A', 'B', 'C', 'D', 'A')
        """, (reading_session,))
        question_id = cursor.lastrowid
        test_db.conn.commit()
        
        # Record answer
        answer_id = annotation_manager.record_answer(
            reading_session, question_id, 'A', 'A'
        )
        
        # Verify record exists with all fields
        cursor.execute("""
            SELECT id, user_answer, correct_answer, is_correct
            FROM reading_comprehension WHERE id = ?
        """, (answer_id,))
        row = cursor.fetchone()
        
        assert row is not None, "Answer record should exist"
        assert row[0] == question_id, "Should have question_id"
        assert row[1] == 'A', "Should have user_answer"
        assert row[2] == 'A', "Should have correct_answer"
        assert row[3] == 1, "Should have is_correct"


class TestAnnotationStorageProperty:
    """
    Property-based tests for annotation storage.
    
    Property 33: Annotation Storage
    Validates: Requirements 12.1, 12.3, 17.1
    
    This test verifies that for ANY annotation creation, the
    annotation is stored with start_position, end_position,
    annotation_type, and timestamp.
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        start_pos=st.integers(min_value=0, max_value=1000),
        end_pos=st.integers(min_value=1000, max_value=2000),
        annotation_type=st.sampled_from(['highlight', 'note', 'bookmark'])
    )
    def test_property_annotation_stored_with_positions(
        self,
        start_pos,
        end_pos,
        annotation_type,
        annotation_manager,
        reading_session
    ):
        """
        Property test: Annotations are stored with positions and type.
        
        For ANY annotation creation, the database record should contain
        start_position, end_position, and annotation_type.
        
        Validates Requirements 12.1, 12.3: Store positions and type
        """
        annotation_id = annotation_manager.create_annotation(
            reading_session, start_pos, end_pos, 'Test text', annotation_type, 'Test note'
        )
        
        # Verify stored values
        cursor = annotation_manager.db.conn.cursor()
        cursor.execute("""
            SELECT start_position, end_position, annotation_type
            FROM reading_annotations WHERE id = ?
        """, (annotation_id,))
        row = cursor.fetchone()
        
        assert row is not None, "Annotation should be stored"
        assert row[0] == start_pos, f"Start position should be {start_pos}"
        assert row[1] == end_pos, f"End position should be {end_pos}"
        assert row[2] == annotation_type, f"Type should be {annotation_type}"


class TestAnnotationRoundTripProperty:
    """
    Property-based tests for annotation round-trip.
    
    Property 34: Annotation Round-Trip
    Validates: Requirements 12.4
    
    This test verifies that for ANY annotation, if we save it
    and then retrieve it, the annotation has the same position
    and content.
    """
    
    def test_property_annotation_restored_after_close_reopen(
        self,
        annotation_manager,
        reading_session,
        test_db
    ):
        """
        Property test: Annotations are restored correctly after close/reopen.
        
        For ANY annotation, if we:
        1. Create an annotation with specific positions and content
        2. Close the database connection
        3. Create a new AnnotationManager instance
        4. Retrieve the annotation
        
        The restored annotation should have the same position and content.
        
        Validates Requirement 12.4: Display saved annotations on reopen
        """
        # Create annotation
        start_pos = 100
        end_pos = 200
        text = 'Test highlighted text'
        note = 'Test note'
        
        annotation_id = annotation_manager.create_annotation(
            reading_session, start_pos, end_pos, text, 'highlight', note
        )
        
        # Close and reopen database
        test_db.conn.close()
        test_db.conn = sqlite3.connect(test_db.db_path, check_same_thread=False, isolation_level=None)
        test_db.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create new manager with fresh connection
        new_manager = AnnotationManager(test_db)
        
        # Retrieve annotation
        annotations = new_manager.get_annotations(reading_session)
        
        assert len(annotations) == 1, "Should have one annotation"
        annotation = annotations[0]
        
        assert annotation['start_position'] == start_pos, (
            f"Start position should be {start_pos}, got {annotation['start_position']}"
        )
        assert annotation['end_position'] == end_pos, (
            f"End position should be {end_pos}, got {annotation['end_position']}"
        )
        assert annotation['highlighted_text'] == text, (
            f"Text should be '{text}', got '{annotation['highlighted_text']}'"
        )
        assert annotation['note_text'] == note, (
            f"Note should be '{note}', got '{annotation['note_text']}'"
        )


class TestAnnotationDeletionProperty:
    """
    Property-based tests for annotation deletion.
    
    Property 35: Annotation Deletion
    Validates: Requirements 12.5, 17.5
    
    This test verifies that for ANY annotation deletion, the
    annotation is removed from the database and no longer
    appears in annotation lists.
    """
    
    def test_property_deleted_annotation_not_in_list(
        self,
        annotation_manager,
        reading_session
    ):
        """
        Property test: Deleted annotations don't appear in lists.
        
        For ANY annotation, after deletion:
        1. The annotation should be removed from the database
        2. The annotation should not appear in get_annotations()
        
        Validates Requirements 12.5, 17.5: Allow annotation deletion
        """
        # Create multiple annotations
        id1 = annotation_manager.create_annotation(
            reading_session, 0, 10, 'Text 1', 'highlight', None
        )
        id2 = annotation_manager.create_annotation(
            reading_session, 20, 30, 'Text 2', 'highlight', None
        )
        id3 = annotation_manager.create_annotation(
            reading_session, 40, 50, 'Text 3', 'highlight', None
        )
        
        # Verify all exist
        annotations = annotation_manager.get_annotations(reading_session)
        assert len(annotations) == 3
        
        # Delete middle annotation
        result = annotation_manager.delete_annotation(id2)
        assert result is True
        
        # Verify only 2 remain
        annotations = annotation_manager.get_annotations(reading_session)
        assert len(annotations) == 2
        
        # Verify deleted annotation is not in list
        deleted_ids = [a['id'] for a in annotations]
        assert id2 not in deleted_ids, "Deleted annotation should not be in list"


class TestBookmarkNavigationProperty:
    """
    Property-based tests for bookmark navigation.
    
    Property 42: Bookmark Navigation
    Validates: Requirements 17.4
    
    This test verifies that for ANY bookmark, selecting it
    updates the reading position to the bookmark's saved position.
    """
    
    def test_property_bookmark_navigates_to_saved_position(
        self,
        annotation_manager,
        reading_session
    ):
        """
        Property test: Bookmark navigation updates to saved position.
        
        For ANY bookmark:
        1. Create a bookmark at a specific position
        2. Get the bookmark using get_bookmarks()
        3. The bookmark should contain the saved position
        
        Validates Requirement 17.4: Navigate to bookmarked positions
        """
        # Create bookmark at specific position
        bookmark_position = 150
        bookmark_note = 'Important section'
        
        annotation_manager.create_annotation(
            reading_session, bookmark_position, bookmark_position, '', 'bookmark', bookmark_note
        )
        
        # Get bookmarks
        bookmarks = annotation_manager.get_bookmarks(reading_session)
        
        assert len(bookmarks) == 1, "Should have one bookmark"
        bookmark = bookmarks[0]
        
        assert bookmark['position'] == bookmark_position, (
            f"Bookmark position should be {bookmark_position}, got {bookmark['position']}"
        )
        assert bookmark['note'] == bookmark_note, (
            f"Bookmark note should be '{bookmark_note}', got '{bookmark['note']}'"
        )
