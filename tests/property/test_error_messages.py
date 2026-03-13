"""
Property-based tests for error message handling in ContentManager.

Tests Property 8: Error Messages for Invalid Content
Validates Requirements 1.10, 21.5
"""

import os
import tempfile
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from src.core.database import FlashcardDatabase
from src.features.reader.content_manager import ContentManager
from src.features.reader.exceptions import (
    AttestationRequiredError,
    InvalidContentError,
    FileTooLargeError
)


# Strategy for empty or whitespace-only content
@st.composite
def empty_content(draw):
    """Generate empty or whitespace-only strings."""
    whitespace_chars = [' ', '\t', '\n', '\r', '\xa0']
    length = draw(st.integers(min_value=0, max_value=50))
    if length == 0:
        return ''
    return ''.join(draw(st.lists(
        st.sampled_from(whitespace_chars),
        min_size=length,
        max_size=length
    )))


# Strategy for too-short content (1-99 characters)
@st.composite
def too_short_content(draw):
    """Generate content that is too short (< 100 characters)."""
    length = draw(st.integers(min_value=1, max_value=99))
    return draw(st.text(
        alphabet=st.characters(blacklist_categories=('Cs', 'Cc')),
        min_size=length,
        max_size=length
    ))


class TestErrorMessagesProperty:
    """Property-based tests for error message handling."""
    
    @pytest.fixture
    def db(self):
        """Create a test database."""
        db = FlashcardDatabase(':memory:')
        yield db
        db.close()
    
    @pytest.fixture
    def content_manager(self, db):
        """Create a ContentManager instance."""
        return ContentManager(db)
    
    # Property 8.1: Empty content raises InvalidContentError with descriptive message
    @given(content=empty_content())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_content_raises_descriptive_error(self, content_manager, content):
        with pytest.raises(InvalidContentError) as exc_info:
            content_manager.import_from_paste(
                content=content,
                title="Test",
                language="en",
                user_attestation=True
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 0
        assert "empty" in error_message.lower() or "cannot" in error_message.lower()
    
    # Property 8.2: Too-short content raises InvalidContentError with length info
    @given(content=too_short_content())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_too_short_content_raises_descriptive_error(self, content_manager, content):
        assume(content.strip() != '')
        
        with pytest.raises(InvalidContentError) as exc_info:
            content_manager.import_from_paste(
                content=content,
                title="Test",
                language="en",
                user_attestation=True
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 0
        assert "short" in error_message.lower() or "minimum" in error_message.lower()
        assert "100" in error_message
        assert "character" in error_message.lower()
    
    # Property 8.3: Missing attestation raises AttestationRequiredError
    @given(content=st.text(min_size=100, max_size=500), attestation=st.just(False))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_missing_attestation_raises_descriptive_error(self, content_manager, content, attestation):
        with pytest.raises(AttestationRequiredError) as exc_info:
            content_manager.import_from_paste(
                content=content,
                title="Test",
                language="en",
                user_attestation=attestation
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 0
        assert "legal" in error_message.lower() or "rights" in error_message.lower()
    
    # Property 8.4: File too large raises FileTooLargeError
    def test_file_too_large_raises_descriptive_error(self, content_manager):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
            chunk_size = 1024 * 1024
            for _ in range(6):
                f.write('a' * chunk_size)
        
        try:
            with pytest.raises(FileTooLargeError) as exc_info:
                content_manager.import_from_file(
                    file_path=temp_path,
                    title="Test",
                    language="en",
                    user_attestation=True
                )
            
            error_message = str(exc_info.value)
            assert len(error_message) > 0
            assert "size" in error_message.lower() or "large" in error_message.lower()
            assert "5" in error_message and "MB" in error_message
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # Property 8.5: Non-existent file raises InvalidContentError
    @given(filename=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122), min_size=5, max_size=20))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_nonexistent_file_raises_descriptive_error(self, content_manager, filename):
        file_path = f"/nonexistent/path/{filename}.txt"
        assume(not os.path.exists(file_path))
        
        with pytest.raises(InvalidContentError) as exc_info:
            content_manager.import_from_file(
                file_path=file_path,
                title="Test",
                language="en",
                user_attestation=True
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 0
        assert "not found" in error_message.lower() or "file" in error_message.lower()
    
    # Property 8.6: Truly invalid binary file content
    def test_invalid_file_content_raises_descriptive_error(self, content_manager):
        """Test that files with content too short after decoding raise errors."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            temp_path = f.name
            # Write content that's too short (< 100 chars)
            f.write('Short')
        
        try:
            with pytest.raises(InvalidContentError) as exc_info:
                content_manager.import_from_file(
                    file_path=temp_path,
                    title="Test",
                    language="en",
                    user_attestation=True
                )
            
            error_message = str(exc_info.value)
            assert len(error_message) > 0
            assert "short" in error_message.lower() or "minimum" in error_message.lower()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
