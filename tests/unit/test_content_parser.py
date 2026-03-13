"""
Unit tests for ContentParser class.

Tests text segmentation, encoding support, and structure preservation.
"""

import pytest
import tempfile
from pathlib import Path

from src.features.reader.content_parser import ContentParser


class TestContentParser:
    """Test suite for ContentParser."""
    
    @pytest.fixture
    def parser(self):
        """Create a ContentParser instance."""
        return ContentParser()
    
    # Basic parsing tests
    
    def test_parse_simple_text(self, parser):
        """Test parsing simple text with multiple sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        result = parser.parse_content(text)
        
        assert result['content'] == text
        assert result['sentence_count'] == 3
        assert len(result['sentences']) == 3
        assert result['sentences'][0] == "This is sentence one."
        assert result['word_count'] > 0
    
    def test_parse_multiple_paragraphs(self, parser):
        """Test parsing text with multiple paragraphs."""
        text = """First paragraph with some text.

Second paragraph with more text.

Third paragraph here."""
        
        result = parser.parse_content(text)
        
        assert result['paragraph_count'] == 3
        assert len(result['paragraphs']) == 3
        assert 'First paragraph' in result['paragraphs'][0]
        assert 'Second paragraph' in result['paragraphs'][1]
        assert 'Third paragraph' in result['paragraphs'][2]
    
    def test_empty_text(self, parser):
        """Test parsing empty text."""
        result = parser.parse_content("")
        
        assert result['content'] == ""
        assert result['paragraph_count'] == 0
        assert result['sentence_count'] == 0
        assert result['word_count'] == 0
    
    def test_whitespace_only(self, parser):
        """Test parsing whitespace-only text."""
        result = parser.parse_content("   \n\n   \t  ")
        
        assert result['content'] == ""
        assert result['paragraph_count'] == 0
        assert result['sentence_count'] == 0
    
    # Sentence segmentation tests
    
    def test_segment_sentences_with_punctuation(self, parser):
        """Test sentence segmentation with various punctuation."""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        sentences = parser.segment_sentences(text)
        
        assert len(sentences) == 4
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"
        assert sentences[2] == "Third sentence?"
        assert sentences[3] == "Fourth sentence."
    
    def test_segment_sentences_with_quotes(self, parser):
        """Test sentence segmentation with quotation marks."""
        text = 'He said "Hello." She replied "Hi!" They laughed.'
        sentences = parser.segment_sentences(text)
        
        assert len(sentences) >= 2  # At least the main sentences
        assert 'He said' in sentences[0]
    
    def test_segment_sentences_empty(self, parser):
        """Test sentence segmentation with empty text."""
        sentences = parser.segment_sentences("")
        assert sentences == []
        
        sentences = parser.segment_sentences("   ")
        assert sentences == []
    
    def test_segment_sentences_no_punctuation(self, parser):
        """Test sentence segmentation with no ending punctuation."""
        text = "This is a sentence without ending punctuation"
        sentences = parser.segment_sentences(text)
        
        # Should still return the text as one sentence
        assert len(sentences) == 1
        assert sentences[0] == text
    
    def test_segment_sentences_cjk(self, parser):
        """Test sentence segmentation with CJK punctuation."""
        # Chinese sentences
        text = "这是第一句。这是第二句！这是第三句？"
        sentences = parser.segment_sentences(text)
        
        assert len(sentences) == 3
        assert "这是第一句。" in sentences[0]
        assert "这是第二句！" in sentences[1]
        assert "这是第三句？" in sentences[2]
    
    # Paragraph segmentation tests
    
    def test_segment_paragraphs_double_newline(self, parser):
        """Test paragraph segmentation with double newlines."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        paragraphs = parser.segment_paragraphs(text)
        
        assert len(paragraphs) == 3
        assert paragraphs[0] == "Paragraph one."
        assert paragraphs[1] == "Paragraph two."
        assert paragraphs[2] == "Paragraph three."
    
    def test_segment_paragraphs_multiple_newlines(self, parser):
        """Test paragraph segmentation with multiple newlines."""
        text = "Paragraph one.\n\n\n\nParagraph two."
        paragraphs = parser.segment_paragraphs(text)
        
        assert len(paragraphs) == 2
        assert paragraphs[0] == "Paragraph one."
        assert paragraphs[1] == "Paragraph two."
    
    def test_segment_paragraphs_single_newline(self, parser):
        """Test that single newlines don't create new paragraphs."""
        text = "Line one.\nLine two.\nLine three."
        paragraphs = parser.segment_paragraphs(text)
        
        # Should be treated as one paragraph
        assert len(paragraphs) == 1
        assert "Line one." in paragraphs[0]
        assert "Line two." in paragraphs[0]
    
    def test_segment_paragraphs_empty(self, parser):
        """Test paragraph segmentation with empty text."""
        paragraphs = parser.segment_paragraphs("")
        assert paragraphs == []
        
        paragraphs = parser.segment_paragraphs("\n\n\n")
        assert paragraphs == []
    
    # Text normalization tests
    
    def test_normalize_text_whitespace(self, parser):
        """Test text normalization removes excessive whitespace."""
        text = "This  has   multiple    spaces."
        normalized = parser.normalize_text(text)
        
        assert normalized == "This has multiple spaces."
    
    def test_normalize_text_line_endings(self, parser):
        """Test text normalization handles different line endings."""
        # Windows line endings
        text_windows = "Line one.\r\nLine two."
        normalized = parser.normalize_text(text_windows)
        assert '\r' not in normalized
        assert normalized == "Line one.\nLine two."
        
        # Old Mac line endings
        text_mac = "Line one.\rLine two."
        normalized = parser.normalize_text(text_mac)
        assert '\r' not in normalized
        assert normalized == "Line one.\nLine two."
    
    def test_normalize_text_strips_edges(self, parser):
        """Test text normalization strips leading/trailing whitespace."""
        text = "  \n  Content here.  \n  "
        normalized = parser.normalize_text(text)
        
        assert normalized == "Content here."
        assert not normalized.startswith(' ')
        assert not normalized.endswith(' ')
    
    # File reading tests
    
    def test_read_file_utf8(self, parser):
        """Test reading UTF-8 encoded file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                         delete=False, suffix='.txt') as f:
            f.write("Hello, world! 你好世界")
            temp_path = f.name
        
        try:
            content, encoding = parser.read_file_with_encoding(temp_path)
            assert content == "Hello, world! 你好世界"
            assert encoding == 'utf-8'
        finally:
            Path(temp_path).unlink()
    
    def test_read_file_utf16(self, parser):
        """Test reading UTF-16 encoded file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-16', 
                                         delete=False, suffix='.txt') as f:
            f.write("UTF-16 content here")
            temp_path = f.name
        
        try:
            content, encoding = parser.read_file_with_encoding(temp_path)
            assert content == "UTF-16 content here"
            assert encoding == 'utf-16'
        finally:
            Path(temp_path).unlink()
    
    def test_read_file_latin1(self, parser):
        """Test reading Latin-1 encoded file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='latin-1', 
                                         delete=False, suffix='.txt') as f:
            f.write("Café résumé")
            temp_path = f.name
        
        try:
            content, encoding = parser.read_file_with_encoding(temp_path)
            assert "Caf" in content  # Should read successfully
            assert encoding in ['utf-8', 'latin-1']  # Could be either
        finally:
            Path(temp_path).unlink()
    
    def test_read_file_not_found(self, parser):
        """Test reading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            parser.read_file_with_encoding("/nonexistent/file.txt")
    
    def test_parse_file(self, parser):
        """Test parsing a complete file."""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                         delete=False, suffix='.txt') as f:
            f.write("First paragraph.\n\nSecond paragraph.")
            temp_path = f.name
        
        try:
            result = parser.parse_file(temp_path)
            
            assert 'encoding' in result
            assert result['encoding'] == 'utf-8'
            assert result['paragraph_count'] == 2
            assert 'First paragraph' in result['content']
        finally:
            Path(temp_path).unlink()
    
    # Pretty print tests
    
    def test_pretty_print(self, parser):
        """Test pretty printing paragraphs."""
        paragraphs = ["First paragraph.", "Second paragraph.", "Third paragraph."]
        formatted = parser.pretty_print(paragraphs)
        
        assert formatted == "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    
    def test_pretty_print_empty(self, parser):
        """Test pretty printing empty list."""
        formatted = parser.pretty_print([])
        assert formatted == ""
    
    def test_pretty_print_single(self, parser):
        """Test pretty printing single paragraph."""
        formatted = parser.pretty_print(["Only paragraph."])
        assert formatted == "Only paragraph."
    
    # Round-trip tests (parse -> pretty print -> parse)
    
    def test_round_trip_preservation(self, parser):
        """Test that parse -> pretty print -> parse preserves structure."""
        original_text = """First paragraph with content.

Second paragraph here.

Third paragraph."""
        
        # First parse
        result1 = parser.parse_content(original_text)
        
        # Pretty print
        formatted = parser.pretty_print(result1['paragraphs'])
        
        # Second parse
        result2 = parser.parse_content(formatted)
        
        # Should have same structure
        assert result1['paragraph_count'] == result2['paragraph_count']
        assert result1['paragraphs'] == result2['paragraphs']
    
    # Word count tests
    
    def test_word_count_simple(self, parser):
        """Test word count for simple text."""
        text = "One two three four five."
        result = parser.parse_content(text)
        
        assert result['word_count'] == 5
    
    def test_word_count_multiple_paragraphs(self, parser):
        """Test word count across multiple paragraphs."""
        text = "First paragraph.\n\nSecond paragraph."
        result = parser.parse_content(text)
        
        assert result['word_count'] == 4
    
    def test_word_count_empty(self, parser):
        """Test word count for empty text."""
        result = parser.parse_content("")
        assert result['word_count'] == 0
    
    # Edge cases
    
    def test_parse_very_long_text(self, parser):
        """Test parsing very long text."""
        # Create a long text with many sentences
        sentences = ["This is sentence number {}.".format(i) for i in range(1000)]
        text = " ".join(sentences)
        
        result = parser.parse_content(text)
        
        assert result['sentence_count'] >= 900  # Should detect most sentences
        assert result['word_count'] > 4000  # Approximate
    
    def test_parse_unicode_content(self, parser):
        """Test parsing content with various Unicode characters."""
        text = """English text here.

中文内容在这里。

한국어 내용입니다.

Текст на русском языке."""
        
        result = parser.parse_content(text)
        
        assert result['paragraph_count'] == 4
        assert '中文' in result['content']
        assert '한국어' in result['content']
        assert 'Текст' in result['content']
    
    def test_parse_mixed_punctuation(self, parser):
        """Test parsing with mixed punctuation styles."""
        text = "Question? Answer! Statement. Another... Ellipsis."
        sentences = parser.segment_sentences(text)
        
        # Should handle various punctuation
        assert len(sentences) >= 3
    
    # Property-based tests
    
    def test_property_content_segmentation(self, parser):
        """
        Property 5: Content Segmentation
        Validates: Requirements 1.5
        
        Property: For all non-empty content strings, parsing produces
        at least 1 sentence and at least 1 paragraph.
        """
        # Test with various non-empty content examples
        test_cases = [
            # Simple sentence
            "This is a sentence.",
            # Multiple sentences
            "First sentence. Second sentence.",
            # Single word
            "Word",
            # Paragraph with newlines
            "Paragraph one.\n\nParagraph two.",
            # Content without punctuation
            "Content without ending punctuation",
            # CJK content
            "这是一个句子。",
            # Mixed content
            "English and 한국어 mixed.",
            # Long content
            " ".join(["Sentence {}.".format(i) for i in range(10)]),
            # Content with special characters
            "Hello! How are you? I'm fine.",
            # Minimal content
            "A",
        ]
        
        for content in test_cases:
            result = parser.parse_content(content)
            
            # Property: Non-empty content must produce >= 1 sentence
            assert result['sentence_count'] >= 1, \
                f"Non-empty content '{content[:50]}...' produced {result['sentence_count']} sentences, expected >= 1"
            
            # Property: Non-empty content must produce >= 1 paragraph
            assert result['paragraph_count'] >= 1, \
                f"Non-empty content '{content[:50]}...' produced {result['paragraph_count']} paragraphs, expected >= 1"
            
            # Additional invariants
            assert len(result['sentences']) >= 1, \
                f"Sentences list should have >= 1 element for non-empty content"
            
            assert len(result['paragraphs']) >= 1, \
                f"Paragraphs list should have >= 1 element for non-empty content"
            
            # Verify counts match list lengths
            assert result['sentence_count'] == len(result['sentences']), \
                f"Sentence count {result['sentence_count']} doesn't match sentences list length {len(result['sentences'])}"
            
            assert result['paragraph_count'] == len(result['paragraphs']), \
                f"Paragraph count {result['paragraph_count']} doesn't match paragraphs list length {len(result['paragraphs'])}"
    
    def test_property_parser_round_trip(self, parser):
        """
        Property 47: Content Parser Round-Trip
        Validates: Requirements 21.4
        
        Property: For all valid imported content, parsing then pretty printing
        then parsing SHALL produce equivalent structured content.
        
        Formally: parse(pretty_print(parse(content).paragraphs)).paragraphs == parse(content).paragraphs
        """
        # Test with various content examples that should round-trip correctly
        test_cases = [
            # Simple single paragraph
            "This is a single paragraph.",
            
            # Multiple paragraphs with double newlines
            "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
            
            # Paragraphs with multiple sentences
            "First sentence. Second sentence. Third sentence.\n\nAnother paragraph here.",
            
            # Content with various punctuation
            "Question? Answer! Statement.\n\nNext paragraph.",
            
            # CJK content
            "这是第一段。\n\n这是第二段。\n\n这是第三段。",
            
            # Korean content
            "첫 번째 단락입니다.\n\n두 번째 단락입니다.",
            
            # Mixed language content
            "English paragraph.\n\n中文段落。\n\n한국어 단락.",
            
            # Content with quotes
            'He said "Hello." She replied "Hi!"\n\nThey continued talking.',
            
            # Long content with many paragraphs
            "\n\n".join([f"Paragraph number {i}." for i in range(10)]),
            
            # Content with special characters
            "Café résumé naïve.\n\nÜber Äpfel Öl.",
            
            # Content with ellipsis
            "First thought...\n\nSecond thought... continues.",
            
            # Single word
            "Word",
            
            # Multiple short paragraphs
            "A.\n\nB.\n\nC.",
            
            # Paragraph with internal newlines (should be preserved as single paragraph)
            "Line one.\nLine two.\nLine three.",
            
            # Empty lines at edges (should be normalized away)
            "\n\nContent here.\n\n",
        ]
        
        for original_content in test_cases:
            # Step 1: Parse original content
            result1 = parser.parse_content(original_content)
            
            # Step 2: Pretty print the paragraphs
            formatted = parser.pretty_print(result1['paragraphs'])
            
            # Step 3: Parse the formatted content
            result2 = parser.parse_content(formatted)
            
            # Property: The paragraph structure should be equivalent
            assert result1['paragraph_count'] == result2['paragraph_count'], \
                f"Round-trip failed: paragraph count changed from {result1['paragraph_count']} to {result2['paragraph_count']}\n" \
                f"Original: {original_content[:100]}\n" \
                f"After round-trip: {formatted[:100]}"
            
            assert result1['paragraphs'] == result2['paragraphs'], \
                f"Round-trip failed: paragraph content changed\n" \
                f"Original paragraphs: {result1['paragraphs']}\n" \
                f"After round-trip: {result2['paragraphs']}"
            
            # Additional invariants: sentence count should also be preserved
            # (within reasonable tolerance for edge cases in sentence segmentation)
            assert result1['sentence_count'] == result2['sentence_count'], \
                f"Round-trip failed: sentence count changed from {result1['sentence_count']} to {result2['sentence_count']}\n" \
                f"Original: {original_content[:100]}"
            
            # Word count should be preserved (or very close)
            word_count_diff = abs(result1['word_count'] - result2['word_count'])
            assert word_count_diff <= 1, \
                f"Round-trip failed: word count changed significantly from {result1['word_count']} to {result2['word_count']}\n" \
                f"Original: {original_content[:100]}"
    
    def test_property_parser_round_trip_idempotent(self, parser):
        """
        Property 47 (Extended): Parser Round-Trip Idempotence
        
        Property: Multiple round-trips should produce the same result.
        parse(pretty_print(parse(pretty_print(parse(content))))) == parse(pretty_print(parse(content)))
        """
        test_content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        
        # First round-trip
        result1 = parser.parse_content(test_content)
        formatted1 = parser.pretty_print(result1['paragraphs'])
        result2 = parser.parse_content(formatted1)
        
        # Second round-trip
        formatted2 = parser.pretty_print(result2['paragraphs'])
        result3 = parser.parse_content(formatted2)
        
        # Third round-trip
        formatted3 = parser.pretty_print(result3['paragraphs'])
        result4 = parser.parse_content(formatted3)
        
        # All results after first round-trip should be identical (idempotent)
        assert result2['paragraphs'] == result3['paragraphs'] == result4['paragraphs'], \
            "Multiple round-trips should produce identical results (idempotence)"
        
        assert formatted1 == formatted2 == formatted3, \
            "Pretty-printed output should stabilize after first round-trip"
