import os
import re
# Import optional dependencies inside methods to avoid crashes if missing, 
# though we installed them. But safe practice.
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    ebooklib = None
    epub = None

class TextImporter:
    """
    Handles reading and parsing text from various sources:
    - plain text (.txt)
    - subtitles (.srt) - strips timestamps
    - html (.html) - strips tags
    - epub (.epub) - extracts chapter text
    """
    
    @staticmethod
    def import_file(file_path: str) -> str:
        """Auto-detect format by extension and import text."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.txt':
            return TextImporter._read_txt(file_path)
        elif ext == '.srt':
            return TextImporter._read_srt(file_path)
        elif ext in ['.html', '.htm']:
            return TextImporter._read_html(file_path)
        elif ext == '.epub':
            return TextImporter._read_epub(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _read_txt(path: str) -> str:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    @staticmethod
    def _read_srt(path: str) -> str:
        """Parse SRT and return just the dialogue text."""
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # SRT format:
        # 1
        # 00:00:01,000 --> 00:00:04,000
        # Text line 1
        # Text line 2
        #
        # 2
        # ...
        
        # Regex to remove index and timestamps
        # 1. Remove timestamps: 00:00:00,000 --> ...
        content = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
        
        # 2. Remove numeric indices (lines that are just digits)
        # Be careful not to remove digits in text. SRT indices are on their own line.
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line: continue
            if line.isdigit(): continue
            lines.append(line)
            
        return "\n".join(lines)

    @staticmethod
    def _read_html(path: str) -> str:
        if not BeautifulSoup:
            return "Error: beautifulsoup4 library not installed."
            
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text
        text = soup.get_text()
        
        # Collapse whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return '\n'.join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _read_epub(path: str) -> str:
        if not ebooklib:
            return "Error: ebooklib library not installed."
            
        book = epub.read_epub(path)
        full_text = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # ITEM_DOCUMENT is HTML content
                if BeautifulSoup:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text = soup.get_text()
                    full_text.append(text)
                else:
                    full_text.append(str(item.get_content()))
                    
        return "\n\n".join(full_text)
