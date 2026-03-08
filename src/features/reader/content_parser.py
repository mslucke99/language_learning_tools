"""
Content parser for Immersive Reading Mode.

Handles text segmentation, encoding detection, and structure preservation
for imported reading content.
"""

import re
from typing import Dict, List, Tuple
from pathlib import Path


class ContentParser:
    """
    Parses and segments text content for reading sessions.
    
    Supports:
    - UTF-8, UTF-16, and Latin-1 encodings
    - Sentence boundary detection
    - Paragraph break preservation
    - Text normalization
    """
    
    # Sentence boundary patterns
    # Matches periods, question marks, exclamation marks followed by space/newline
    # Handles common abbreviations and edge cases
    SENTENCE_ENDINGS = re.compile(
        r'([.!?]+[\'"»\]\)]*)\s+(?=[A-ZÀ-ÖØ-Þ\u4E00-\u9FFF\uAC00-\uD7AF])',
        re.UNICODE
    )
    
    # Paragraph break patterns (two or more newlines)
    PARAGRAPH_BREAKS = re.compile(r'\n\s*\n+', re.UNICODE)
    
    # Supported encodings in order of preference
    ENCODINGS = ['utf-8', 'utf-16', 'latin-1']
    
    def __init__(self):
        """Initialize the ContentParser."""
        pass
    
    def read_file_with_encoding(self, file_path: str) -> Tuple[str, str]:
        """
        Read a file with automatic encoding detection.
        
        Tries encodings in order: UTF-8, UTF-16, Latin-1
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Tuple of (content, encoding_used)
            
        Raises:
            IOError: If file cannot be read with any supported encoding
            FileNotFoundError: If file does not exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise IOError(f"Path is not a file: {file_path}")
        
        # Try each encoding in order
        last_error = None
        for encoding in self.ENCODINGS:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()
                return content, encoding
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
        
        # If all encodings failed, raise the last error
        raise IOError(
            f"Could not read file with any supported encoding "
            f"({', '.join(self.ENCODINGS)}): {last_error}"
        )
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text content.
        
        - Removes excessive whitespace
        - Normalizes line endings to \n
        - Strips leading/trailing whitespace
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text
        """
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive spaces (but preserve single spaces)
        text = re.sub(r' +', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def segment_paragraphs(self, text: str) -> List[str]:
        """
        Segment text into paragraphs.
        
        Paragraphs are separated by two or more newlines.
        Preserves paragraph structure from original text.
        
        Args:
            text: Text content
            
        Returns:
            List of paragraph strings
        """
        # Split on paragraph breaks (2+ newlines)
        paragraphs = self.PARAGRAPH_BREAKS.split(text)
        
        # Filter out empty paragraphs and strip whitespace
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def segment_sentences(self, text: str) -> List[str]:
        """
        Segment text into sentences.
        
        Uses regex-based sentence boundary detection that handles:
        - Common sentence endings (. ! ?)
        - Quotation marks and brackets
        - Capital letter following sentence ending
        - Multiple languages (Latin, CJK, Korean)
        
        Args:
            text: Text content (can be full text or single paragraph)
            
        Returns:
            List of sentence strings
        """
        # Handle empty text
        if not text.strip():
            return []
        
        # For CJK languages, also split on CJK-specific punctuation
        # Chinese: 。！？
        # Japanese: 。！？
        # Korean: . ! ? (uses same as English)
        cjk_endings = re.compile(r'([。！？]+)\s*', re.UNICODE)
        
        # First, handle CJK sentence endings
        text_with_markers = cjk_endings.sub(r'\1\n', text)
        
        # Then handle standard sentence endings
        text_with_markers = self.SENTENCE_ENDINGS.sub(r'\1\n', text_with_markers)
        
        # Split on the markers we inserted
        sentences = text_with_markers.split('\n')
        
        # Filter out empty sentences and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def parse_content(self, text: str) -> Dict:
        """
        Parse text content into structured format.
        
        Args:
            text: Raw text content
            
        Returns:
            Dictionary containing:
            - content: Normalized full text
            - paragraphs: List of paragraph strings
            - sentences: List of all sentences
            - paragraph_count: Number of paragraphs
            - sentence_count: Number of sentences
            - word_count: Approximate word count
        """
        # Normalize the text
        normalized = self.normalize_text(text)
        
        # Segment into paragraphs
        paragraphs = self.segment_paragraphs(normalized)
        
        # Segment into sentences (from full text)
        sentences = self.segment_sentences(normalized)
        
        # Calculate word count (approximate, space-separated)
        # This works reasonably well for most languages
        word_count = len(normalized.split())
        
        return {
            'content': normalized,
            'paragraphs': paragraphs,
            'sentences': sentences,
            'paragraph_count': len(paragraphs),
            'sentence_count': len(sentences),
            'word_count': word_count
        }
    
    def parse_file(self, file_path: str) -> Dict:
        """
        Parse a text file into structured format.
        
        Automatically detects encoding and parses content.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Dictionary containing parsed content (same as parse_content)
            plus 'encoding' field
            
        Raises:
            IOError: If file cannot be read
            FileNotFoundError: If file does not exist
        """
        # Read file with encoding detection
        content, encoding = self.read_file_with_encoding(file_path)
        
        # Parse the content
        result = self.parse_content(content)
        
        # Add encoding information
        result['encoding'] = encoding
        
        return result
    
    def pretty_print(self, paragraphs: List[str]) -> str:
        """
        Format paragraphs into readable text with consistent spacing.
        
        Args:
            paragraphs: List of paragraph strings
            
        Returns:
            Formatted text with double newlines between paragraphs
        """
        return '\n\n'.join(paragraphs)
