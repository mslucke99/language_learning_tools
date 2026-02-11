import importlib
from typing import List, Dict, Optional

class Token:
    def __init__(self, text: str, lemma: str = "", pos: str = "", start: int = 0, end: int = 0):
        self.text = text
        self.lemma = lemma if lemma else text
        self.pos = pos
        self.start = start
        self.end = end

    def to_dict(self):
        return {
            "text": self.text,
            "lemma": self.lemma,
            "pos": self.pos,
            "start": self.start,
            "end": self.end
        }

class TokenizerService:
    """
    A facade for various tokenization libraries strategies.
    Supported Backends:
    - 'kiwipiepy' -> Korean (Best)
    - 'jieba' -> Chinese (Standard)
    - 'spacy' -> European / Japanese (Robust)
    - 'whitespace' -> Fallback
    """
    
    def __init__(self):
        self._cache = {}  # Cache for loaded models (e.g. Kiwi instance)

    def tokenize(self, text: str, lang_code: str) -> List[Token]:
        """
        Main entry point. Routes to specific tokenizer based on language.
        """
        if not text:
            return []

        if lang_code == "ko":
            return self._tokenize_korean(text)
        elif lang_code in ["zh", "zh-CN", "zh-TW"]:
            return self._tokenize_chinese(text)
        elif lang_code == "ja":
            return self._tokenize_japanese(text)
        else:
            # Default to space-based or spacy if available
            return self._tokenize_european(text, lang_code)

    def _tokenize_korean(self, text: str) -> List[Token]:
        """Uses kiwipiepy for Korean."""
        try:
            # Lazy load Kiwi
            if "kiwi" not in self._cache:
                from kiwipiepy import Kiwi
                self._cache["kiwi"] = Kiwi()
                
            kiwi = self._cache["kiwi"]
            tokens = []
            results = kiwi.tokenize(text)
            
            # Kiwi result properties: form, tag, start, len
            for t in results:
                tokens.append(Token(
                    text=t.form,
                    lemma=t.form,  # Use form as lemma for now
                    pos=t.tag,
                    start=t.start,
                    end=t.start + t.len
                ))
            return tokens

        except ImportError:
            print("Warning: 'kiwipiepy' not installed. Korean tokenization will be poor.")
            print("Run: pip install kiwipiepy")
            return self._tokenize_whitespace(text)

    def _tokenize_chinese(self, text: str) -> List[Token]:
        """Uses jieba for Chinese."""
        try:
            import jieba
            # jieba.tokenize returns generator of (word, start, end)
            tokens = []
            for word, start, end in jieba.tokenize(text):
                tokens.append(Token(word, word, "UNK", start, end))
            return tokens
        except ImportError:
            print("Warning: 'jieba' not installed. Chinese tokenization will be poor.")
            print("Run: pip install jieba")
            return self._tokenize_whitespace(text)

    def _tokenize_japanese(self, text: str) -> List[Token]:
        """Try spaCy first, then nagisa."""
        # TODO: Implement Nagisa/Spacy fallback
        # For now, simplistic fallback
        return self._tokenize_whitespace(text)

    def _tokenize_european(self, text: str, lang_code: str) -> List[Token]:
        # TODO: integrate spaCy here
        return self._tokenize_whitespace(text)

    def _tokenize_whitespace(self, text: str) -> List[Token]:
        """Simple fallback splitter using regex to separate punctuation."""
        import re
        tokens = []
        # Pattern: words (alphanumeric) OR non-whitespace symbols
        matches = re.finditer(r'\w+|[^\w\s]', text, re.UNICODE)
        
        for m in matches:
            word = m.group()
            start = m.start()
            end = m.end()
            tokens.append(Token(word, word, "UNK", start, end))
            
        return tokens
