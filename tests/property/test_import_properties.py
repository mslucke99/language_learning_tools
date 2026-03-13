"""
Property-based tests for Immersive Reading Mode content import.

These tests verify that content import operations correctly store all required
fields and maintain data integrity across various input scenarios.

Property 1: Content Import Stores All Required Fields
- Validates: Requirements 1.1, 1.2, 1.8, 1.9, 2.1
- Verifies created Reading_Session contains all required fields
"""

import tempfile
import os
import pytest
from hypothesis import given, strategies as st, settings
from src.core.database import FlashcardDatabase
from src.features.reader.content_manager import ContentManager


class TestContentImportRequiredFields:
    """
    Property 1: Content Import Stores All Required Fields
    
    This property ensures that when content is imported (via paste or file),
    the created Reading_Session record contains ALL required fields with
    appropriate values. This validates that the import process correctly
    captures and stores all necessary metadata for legal compliance,
    content management, and user experience.
    
    Required fields verified:
    - user_id: User who imported the content
    - title: User-provided title
    - content: The actual text content
    - language: Target language code
    - source: Origin of content ('user_paste' or 'user_file')
    - import_method: Method used ('paste' or 'file')
    - difficulty_score: Calculated difficulty (0.0-1.0)
    - difficulty_rating: Rating category ('easy', 'medium', 'hard')
    - word_count: Number of words in content
    - estimated_minutes: Estimated reading time
    - legal_attestation: Must be TRUE (1)
    - private: Must be TRUE (1)
    - shareable: Must be FALSE (0)
    - created_at: Timestamp of creation
    """

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def db(self, temp_db):
        """Create a FlashcardDatabase instance."""
        database = FlashcardDatabase(db_name=temp_db)
        yield database
        database.close()

    @pytest.fixture
    def content_manager(self, db):
        """Create a ContentManager instance."""
        return ContentManager(db)

    def _verify_required_fields(
        self,
        db: FlashcardDatabase,
        session_id: int,
        expected_title: str,
        expected_content: str,
        expected_language: str,
        expected_source: str,
        expected_import_method: str,
        expected_user_id: int = 1
    ) -> None:
        """
        Helper method to verify all required fields are present and valid.
        
        Args:
            db: Database instance
            session_id: ID of the reading session to verify
            expected_title: Expected title value
            expected_content: Expected content value
            expected_language: Expected language code
            expected_source: Expected source ('user_paste' or 'user_file')
            expected_import_method: Expected method ('paste' or 'file')
            expected_user_id: Expected user ID (default: 1)
            
        Raises:
            AssertionError: If any required field is missing or invalid
        """
        cursor = db.conn.cursor()
        
        # Fetch the reading session
        cursor.execute("""
            SELECT 
                user_id, title, content, language, source, import_method,
                difficulty_score, difficulty_rating, word_count, estimated_minutes,
                legal_attestation, private, shareable, created_at,
                import_ip_address, import_user_agent
            FROM reading_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        assert row is not None, f"Reading session {session_id} not found"
        
        (user_id, title, content, language, source, import_method,
         difficulty_score, difficulty_rating, word_count, estimated_minutes,
         legal_attestation, private, shareable, created_at,
         import_ip_address, import_user_agent) = row
        
        # Verify core identification fields
        assert user_id == expected_user_id, \
            f"user_id mismatch: expected {expected_user_id}, got {user_id}"
        
        assert title == expected_title, \
            f"title mismatch: expected '{expected_title}', got '{title}'"
        
        assert content is not None and len(content) > 0, \
            "content must not be empty"
        
        # Content should be normalized version of expected_content
        # Normalize line endings for comparison (Windows vs Unix)
        normalized_expected = expected_content.strip().replace('\r\n', '\n').replace('\r', '\n')
        normalized_content = content.strip().replace('\r\n', '\n').replace('\r', '\n')
        assert normalized_expected in normalized_content or normalized_content in normalized_expected, \
            f"content does not match expected content"
        
        assert language == expected_language, \
            f"language mismatch: expected '{expected_language}', got '{language}'"
        
        # Verify import metadata
        assert source == expected_source, \
            f"source mismatch: expected '{expected_source}', got '{source}'"
        
        assert import_method == expected_import_method, \
            f"import_method mismatch: expected '{expected_import_method}', got '{import_method}'"
        
        # Verify calculated fields
        assert difficulty_score is not None, "difficulty_score must not be NULL"
        assert 0.0 <= difficulty_score <= 1.0, \
            f"difficulty_score must be in [0.0, 1.0], got {difficulty_score}"
        
        assert difficulty_rating is not None, "difficulty_rating must not be NULL"
        assert difficulty_rating in ['easy', 'medium', 'hard'], \
            f"difficulty_rating must be 'easy', 'medium', or 'hard', got '{difficulty_rating}'"
        
        assert word_count is not None, "word_count must not be NULL"
        assert word_count > 0, f"word_count must be positive, got {word_count}"
        
        assert estimated_minutes is not None, "estimated_minutes must not be NULL"
        assert estimated_minutes > 0, \
            f"estimated_minutes must be positive, got {estimated_minutes}"
        
        # Verify legal compliance fields
        assert legal_attestation == 1, \
            f"legal_attestation must be TRUE (1), got {legal_attestation}"
        
        assert private == 1, \
            f"private must be TRUE (1), got {private}"
        
        assert shareable == 0, \
            f"shareable must be FALSE (0), got {shareable}"
        
        # Verify timestamp
        assert created_at is not None, "created_at must not be NULL"
        
        # Note: import_ip_address and import_user_agent are optional (can be NULL)
        # but we verify they are present in the schema
        
        # Verify difficulty_rating matches difficulty_score
        if difficulty_score < 0.33:
            assert difficulty_rating == 'easy', \
                f"difficulty_rating should be 'easy' for score {difficulty_score}"
        elif difficulty_score < 0.67:
            assert difficulty_rating == 'medium', \
                f"difficulty_rating should be 'medium' for score {difficulty_score}"
        else:
            assert difficulty_rating == 'hard', \
                f"difficulty_rating should be 'hard' for score {difficulty_score}"

    @given(
        title=st.text(min_size=1, max_size=200),
        content=st.text(min_size=100, max_size=5000).filter(lambda x: len(x.strip()) >= 100),
        language=st.sampled_from(['en', 'ko', 'ja', 'es', 'fr', 'de', 'zh'])
    )
    @settings(max_examples=100, deadline=None)
    def test_import_from_paste_stores_all_required_fields(
        self,
        title,
        content,
        language
    ):
        """
        Property test: import_from_paste stores all required fields.
        
        For ANY valid title, content, and language:
        - Import via paste with attestation=True
        - Verify the created Reading_Session contains ALL required fields
        - Verify all field values are valid and consistent
        
        This test uses hypothesis to generate diverse inputs and verify
        the property holds across a wide range of scenarios.
        """
        # Create fresh temporary database for each hypothesis example
        fd, temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Create fresh database and manager
            db = FlashcardDatabase(db_name=temp_db_path)
            content_manager = ContentManager(db)
            
            # Import content from paste
            session_id = content_manager.import_from_paste(
                content=content,
                title=title,
                language=language,
                user_attestation=True,
                user_id=1,
                import_ip_address='127.0.0.1',
                import_user_agent='pytest/hypothesis'
            )
            
            # Verify all required fields are present and valid
            self._verify_required_fields(
                db=db,
                session_id=session_id,
                expected_title=title,
                expected_content=content,
                expected_language=language,
                expected_source='user_paste',
                expected_import_method='paste',
                expected_user_id=1
            )
            
            # Verify reading_progress entry was also created
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT session_id, user_id, current_position, completion_percentage
                FROM reading_progress
                WHERE session_id = ?
            """, (session_id,))
            
            progress_row = cursor.fetchone()
            assert progress_row is not None, \
                "reading_progress entry must be created with reading_session"
            
            prog_session_id, prog_user_id, current_position, completion_percentage = progress_row
            assert prog_session_id == session_id
            assert prog_user_id == 1
            assert current_position == 0
            assert completion_percentage == 0.0
            
        finally:
            # Close database connection before cleanup
            db.close()
            
            # Cleanup temporary database
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except PermissionError:
                # On Windows, file might still be locked - ignore cleanup error
                pass

    def test_import_from_paste_with_specific_examples(self, content_manager, db):
        """
        Test import_from_paste with specific example inputs.
        
        This complements the property test with concrete examples
        that are easy to debug and understand.
        """
        test_cases = [
            {
                'title': 'Simple English Article',
                'content': 'This is a simple test article. ' * 20,  # 100+ chars
                'language': 'en',
                'user_id': 1
            },
            {
                'title': '한국어 기사',
                'content': '이것은 한국어로 작성된 테스트 기사입니다. ' * 10,
                'language': 'ko',
                'user_id': 1
            },
            {
                'title': 'Long Technical Document',
                'content': (
                    'The implementation of distributed systems requires careful '
                    'consideration of consistency, availability, and partition tolerance. '
                ) * 30,
                'language': 'en',
                'user_id': 2
            }
        ]
        
        for test_case in test_cases:
            session_id = content_manager.import_from_paste(
                content=test_case['content'],
                title=test_case['title'],
                language=test_case['language'],
                user_attestation=True,
                user_id=test_case['user_id'],
                import_ip_address='192.168.1.1',
                import_user_agent='Mozilla/5.0'
            )
            
            self._verify_required_fields(
                db=db,
                session_id=session_id,
                expected_title=test_case['title'],
                expected_content=test_case['content'],
                expected_language=test_case['language'],
                expected_source='user_paste',
                expected_import_method='paste',
                expected_user_id=test_case['user_id']
            )

    def test_import_from_file_stores_all_required_fields(
        self,
        content_manager,
        db,
        tmp_path
    ):
        """
        Test that import_from_file stores all required fields.
        
        Creates temporary files with various content and verifies
        that all required fields are stored correctly.
        """
        test_cases = [
            {
                'title': 'File Import Test 1',
                'content': 'This is content from a file. ' * 20,
                'language': 'en',
                'filename': 'test1.txt'
            },
            {
                'title': 'Markdown File',
                'content': '# Heading\n\nThis is markdown content. ' * 15,
                'language': 'en',
                'filename': 'test2.md'
            },
            {
                'title': 'UTF-8 Content',
                'content': 'Unicode test: 你好世界 こんにちは 안녕하세요 ' * 10,
                'language': 'zh',
                'filename': 'test3.txt'
            }
        ]
        
        for test_case in test_cases:
            # Create temporary file
            file_path = tmp_path / test_case['filename']
            file_path.write_text(test_case['content'], encoding='utf-8')
            
            # Import from file
            session_id = content_manager.import_from_file(
                file_path=str(file_path),
                title=test_case['title'],
                language=test_case['language'],
                user_attestation=True,
                user_id=1,
                import_ip_address='10.0.0.1',
                import_user_agent='FileImporter/1.0'
            )
            
            # Verify all required fields
            self._verify_required_fields(
                db=db,
                session_id=session_id,
                expected_title=test_case['title'],
                expected_content=test_case['content'],
                expected_language=test_case['language'],
                expected_source='user_file',
                expected_import_method='file',
                expected_user_id=1
            )

    def test_import_stores_audit_trail_fields(self, content_manager, db):
        """
        Test that import operations store audit trail information.
        
        Verifies that import_ip_address and import_user_agent are
        correctly stored for legal compliance tracking.
        """
        test_ip = '203.0.113.42'
        test_user_agent = 'TestBrowser/1.0 (Testing)'
        
        session_id = content_manager.import_from_paste(
            content='Test content for audit trail verification. ' * 10,
            title='Audit Trail Test',
            language='en',
            user_attestation=True,
            user_id=1,
            import_ip_address=test_ip,
            import_user_agent=test_user_agent
        )
        
        # Verify audit trail fields
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT import_ip_address, import_user_agent
            FROM reading_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        
        ip_address, user_agent = row
        assert ip_address == test_ip, \
            f"import_ip_address mismatch: expected '{test_ip}', got '{ip_address}'"
        assert user_agent == test_user_agent, \
            f"import_user_agent mismatch: expected '{test_user_agent}', got '{user_agent}'"

    def test_import_without_audit_trail_still_creates_session(
        self,
        content_manager,
        db
    ):
        """
        Test that import works even without audit trail information.
        
        Audit trail fields (IP address, user agent) are optional,
        so import should succeed even when they are not provided.
        """
        session_id = content_manager.import_from_paste(
            content='Test content without audit trail. ' * 10,
            title='No Audit Trail Test',
            language='en',
            user_attestation=True,
            user_id=1,
            import_ip_address=None,
            import_user_agent=None
        )
        
        # Verify session was created
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT id, import_ip_address, import_user_agent
            FROM reading_sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        assert row is not None
        
        session_id_db, ip_address, user_agent = row
        assert session_id_db == session_id
        # Audit trail fields should be NULL
        assert ip_address is None
        assert user_agent is None

    def test_multiple_imports_all_have_required_fields(self, content_manager, db):
        """
        Test that multiple sequential imports all store required fields.
        
        Verifies that the property holds across multiple operations
        and that each session is independent and complete.
        """
        sessions = []
        
        for i in range(10):
            session_id = content_manager.import_from_paste(
                content=f'Test content for session {i}. ' * 20,
                title=f'Session {i}',
                language='en' if i % 2 == 0 else 'ko',
                user_attestation=True,
                user_id=(i % 3) + 1,
                import_ip_address=f'192.168.1.{i}',
                import_user_agent=f'TestAgent/{i}'
            )
            sessions.append({
                'id': session_id,
                'title': f'Session {i}',
                'language': 'en' if i % 2 == 0 else 'ko',
                'user_id': (i % 3) + 1
            })
        
        # Verify all sessions have required fields
        for session in sessions:
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT user_id, title, language, difficulty_score, 
                       word_count, legal_attestation, private, shareable
                FROM reading_sessions
                WHERE id = ?
            """, (session['id'],))
            
            row = cursor.fetchone()
            assert row is not None, f"Session {session['id']} not found"
            
            (user_id, title, language, difficulty_score,
             word_count, legal_attestation, private, shareable) = row
            
            assert user_id == session['user_id']
            assert title == session['title']
            assert language == session['language']
            assert difficulty_score is not None
            assert word_count > 0
            assert legal_attestation == 1
            assert private == 1
            assert shareable == 0

    def test_import_with_different_encodings(self, content_manager, db, tmp_path):
        """
        Test that file imports with different encodings store all required fields.
        
        Verifies that the property holds regardless of file encoding.
        """
        test_cases = [
            {
                'content': 'UTF-8 encoded content. ' * 10,
                'encoding': 'utf-8',
                'language': 'en'
            },
            {
                'content': 'UTF-16 encoded content. ' * 10,
                'encoding': 'utf-16',
                'language': 'en'
            },
            {
                'content': 'Latin-1 encoded content. ' * 10,
                'encoding': 'latin-1',
                'language': 'en'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Create file with specific encoding
            file_path = tmp_path / f'encoding_test_{i}.txt'
            file_path.write_text(test_case['content'], encoding=test_case['encoding'])
            
            # Import file
            session_id = content_manager.import_from_file(
                file_path=str(file_path),
                title=f'Encoding Test {test_case["encoding"]}',
                language=test_case['language'],
                user_attestation=True,
                user_id=1
            )
            
            # Verify all required fields are present
            self._verify_required_fields(
                db=db,
                session_id=session_id,
                expected_title=f'Encoding Test {test_case["encoding"]}',
                expected_content=test_case['content'],
                expected_language=test_case['language'],
                expected_source='user_file',
                expected_import_method='file',
                expected_user_id=1
            )
