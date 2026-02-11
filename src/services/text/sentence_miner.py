import re
from typing import List, Dict, Tuple
from src.core.database import FlashcardDatabase
from src.services.text.tokenizer_service import TokenizerService, Token
from src.services.dictionary.dictionary_manager import DictionaryEngine

class SentenceResult:
    def __init__(self, text: str, tokens: List[Token], unknown_words: List[Token], level: int):
        self.text = text
        self.tokens = tokens
        self.unknown_words = unknown_words
        self.level = level  # 0 = i+0 (all known), 1 = i+1, etc.
        
    def to_dict(self):
        return {
            "text": self.text,
            "tokens": [t.__dict__ for t in self.tokens],
            "unknown_words": [t.__dict__ for t in self.unknown_words],
            "level": self.level
        }

class MiningResult:
    def __init__(self, sentences: List[SentenceResult]):
        self.sentences = sentences
        # Stats
        self.total_sentences = len(sentences)
        self.i0_count = sum(1 for s in sentences if s.level == 0)
        self.i1_count = sum(1 for s in sentences if s.level == 1)
        self.i2_plus_count = sum(1 for s in sentences if s.level > 1)
        
        # Aggregate unique unknown words for the sidebar
        self.all_unknown_words = {}
        for s in sentences:
            for t in s.unknown_words:
                self.all_unknown_words[t.lemma] = t

class SentenceMiner:
    def __init__(self, db: FlashcardDatabase, tokenizer: TokenizerService):
        self.db = db
        self.tokenizer = tokenizer
        
    def analyze_text(self, text: str, lang_code: str) -> MiningResult:
        """
        Split text into sentences and classify each by difficulty level.
        """
        # 1. Split text
        sentences_text = self._split_sentences(text)
        
        # 2. Get known words cache for performance? 
        # For a long book, querying DB for every token is slow.
        # But we have `is_word_known` which is a single query.
        # Better: get ALL known words for this language into a set first.
        known_set = self._load_known_vocabulary(lang_code)
        
        results = []
        
        for sent_text in sentences_text:
            if not sent_text.strip():
                continue
                
            # Tokenize
            tokens = self.tokenizer.tokenize(sent_text, lang_code)
            
            # Filter tokens that are actually words (ignore punctuation in unknown count)
            # We assume TokenizerService.Token has a POS or we check if lemma is punctuation
            # For now, strict check: if it has a lemma, we check it.
            
            unknown = []
            for t in tokens:
                # Skip punctuation/spaces if possible. 
                # Kiwipiepy/Jieba return punctuation as tokens. 
                # Simple heuristic: if lemma contains only symbols/punctuation, skip.
                if self._is_punctuation(t.lemma):
                    continue
                    
                if t.lemma.lower() not in known_set:
                    unknown.append(t)
            
            level = len(unknown)
            results.append(SentenceResult(sent_text, tokens, unknown, level))
            
        return MiningResult(results)

    def _split_sentences(self, text: str) -> List[str]:
        """
        Robust sentence splitting for multiple languages.
        Splits by newlines first, then by standard sentence terminators
        ONLY if they are followed by whitespace or are at the end of a line.
        This protects decimals (0.8), dates (2026.02.07), and URLs/emails.
        """
        # 1. Normalize line endings
        text = text.replace('\r\n', '\n')
        
        # 2. Split by newlines first (treat lines as primary boundaries)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        sentences = []
        
        # 3. Pattern: Greedy match for terminators, but only if followed by space or end of string.
        # Capture group pattern: ([terminators])
        pattern = r'([.!?。！？]+(?=\s|$))'
        
        for line in lines:
            # Skip complex splitting if no terminators are even present
            if not any(c in line for c in ".!?。！？"):
                sentences.append(line)
                continue
                
            chunks = re.split(pattern, line)
            
            # re.split with one capture group -> [text, delim, text, delim, ..., text]
            i = 0
            while i < len(chunks) - 1:
                # Combine text with following delimiter
                combined = (chunks[i] + chunks[i+1]).strip()
                if combined:
                    sentences.append(combined)
                i += 2
                
            # Handle the last text chunk if it wasn't followed by a delimiter
            if i < len(chunks):
                last_chunk = chunks[i].strip()
                if last_chunk:
                    sentences.append(last_chunk)
                    
        return sentences

    def _load_known_vocabulary(self, lang_code: str) -> set:
        """Load all known lemmas for a language into a fast lookup set."""
        words = self.db.get_all_known_words(lang_code)
        return {w['lemma'].lower() for w in words} # Dict returned by DB
        
    def _is_punctuation(self, text: str) -> bool:
        """Check if token is purely punctuation."""
        return not any(c.isalnum() for c in text)
