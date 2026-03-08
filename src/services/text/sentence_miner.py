import re
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from src.core.database import FlashcardDatabase
from src.services.text.tokenizer_service import TokenizerService, Token
from src.services.dictionary.dictionary_manager import DictionaryEngine
from src.services.text.grammar_extractor import GrammarExtractor

if TYPE_CHECKING:
    from src.services.text.sentence_difficulty import SentenceDifficultyScorer

class SentenceResult:
    def __init__(
        self,
        text: str,
        tokens: List[Token],
        unknown_words: List[Token],
        level: int,
        grammar_patterns: List[str] = None,
        *,
        difficulty_score: Optional[float] = None,
        difficulty_confidence: Optional[float] = None,
        category: Optional[str] = None,
        bottleneck_word: Optional[str] = None,
    ):
        self.text = text
        self.tokens = tokens
        self.unknown_words = unknown_words
        self.level = level  # 0 = i+0 (all known), 1 = i+1, etc.
        self.grammar_patterns = grammar_patterns if grammar_patterns else []
        self.difficulty_score = difficulty_score
        self.difficulty_confidence = difficulty_confidence
        self.category = category
        self.bottleneck_word = bottleneck_word

    def to_dict(self):
        d = {
            "text": self.text,
            "tokens": [t.__dict__ for t in self.tokens],
            "unknown_words": [t.__dict__ for t in self.unknown_words],
            "level": self.level,
            "grammar_patterns": self.grammar_patterns,
        }
        if self.difficulty_score is not None:
            d["difficulty_score"] = self.difficulty_score
        if self.difficulty_confidence is not None:
            d["difficulty_confidence"] = self.difficulty_confidence
        if self.category is not None:
            d["category"] = self.category
        if self.bottleneck_word is not None:
            d["bottleneck_word"] = self.bottleneck_word
        return d

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
    def __init__(
        self,
        db: FlashcardDatabase,
        tokenizer: TokenizerService,
        difficulty_scorer: Optional["SentenceDifficultyScorer"] = None,
    ):
        self.db = db
        self.tokenizer = tokenizer
        self.grammar_extractor = GrammarExtractor()
        self.difficulty_scorer = difficulty_scorer

    def analyze_text(self, text: str, lang_code: str) -> MiningResult:
        """
        Split text into sentences and classify each by difficulty level.
        If difficulty_scorer is set, each SentenceResult also gets difficulty_score, category, etc.
        """
        # 1. Split text
        sentences_text = self._split_sentences(text)

        known_set = self._load_known_vocabulary(lang_code)
        ignored_set = self._load_ignored_vocabulary(lang_code)
        results = []

        # 2. Match phrases first using n-grams (up to 5 tokens)
        known_phrases = {k for k in known_set if ' ' in k}
        
        for sent_text in sentences_text:
            if not sent_text.strip():
                continue

            tokens = self.tokenizer.tokenize(sent_text, lang_code)
            
            # Find tokens that belong to a known multi-word phrase
            known_token_indices = set()
            if known_phrases:
                # Try n-grams from 5 down to 2
                for n in range(min(5, len(tokens)), 1, -1):
                    for i in range(len(tokens) - n + 1):
                        # Skip if any token in this range is already marked known
                        if any(j in known_token_indices for j in range(i, i+n)):
                            continue
                            
                        # Check both lemma-based and text-based phrase matching
                        lemma_phrase = " ".join(t.lemma.lower() for t in tokens[i:i+n]).strip()
                        text_phrase = " ".join(t.text.lower() for t in tokens[i:i+n]).strip()
                        
                        if lemma_phrase in known_phrases or text_phrase in known_phrases:
                            for j in range(i, i+n):
                                known_token_indices.add(j)

            unknown = []
            for i, t in enumerate(tokens):
                # 0. Skip if already matched as part of a phrase
                if i in known_token_indices:
                    continue
                    
                # 1. Check if it's explicitly punctuation/number
                if self._is_punctuation(t.lemma):
                    continue

                # 2. Language-specific morphology rules
                if self._should_ignore_token(lang_code, t):
                    continue

                # 3. Check if explicitly marked as a non-word (ignored)
                if t.lemma.lower() in ignored_set:
                    continue

                # 4. Check if known
                is_known = False
                lemma_lower = t.lemma.lower()
                text_lower = t.text.lower()
                
                if lemma_lower in known_set or text_lower in known_set:
                    is_known = True
                elif lang_code == "ko":
                    # Special Korean matching: verb roots often added without '다'
                    if lemma_lower.endswith('다') and lemma_lower[:-1] in known_set:
                        is_known = True
                    # Check if any part of the known set matches the lemma or text (substring)
                    # This is aggressive but helpful for agglutinative languages
                
                if not is_known:
                    unknown.append(t)

            # 3. Grammar patterns
            grammar_patterns = self.grammar_extractor.extract(tokens, lang_code)

            level = len(unknown)
            result = SentenceResult(sent_text, tokens, unknown, level, grammar_patterns)

            results.append(result)

        # 4. Batch Difficulty Scoring (for performance)
        if self.difficulty_scorer:
            sentence_texts = [r.text for r in results]
            score_results = self.difficulty_scorer.score_batch(sentence_texts, lang_code)
            
            for i, res in enumerate(results):
                sr = score_results[i]
                res.difficulty_score = sr.difficulty_score
                res.difficulty_confidence = sr.confidence
                res.category = sr.difficulty_category
                res.bottleneck_word = sr.bottleneck_word

        return MiningResult(results)

    def _should_ignore_token(self, lang_code: str, token: Token) -> bool:
        """
        Check if a token should be ignored for difficulty/unknown counting.
        Usually ignores particles, endings, and purely grammatical markers.
        """
        if lang_code == "ko":
            # Kiwipiepy tags:
            # J* = Particles (Josa)
            # E* = Endings (Eomi)
            # X* = Suffixes ( 접사)
            # S* = Symbols/Punctuation (SF, SP, SS, etc.)
            if token.pos and (
                token.pos.startswith('J') or 
                token.pos.startswith('E') or 
                token.pos.startswith('X') or
                token.pos.startswith('S')
            ):
                return True
        
        elif lang_code == "ja":
            # For Japanese (MeCab/Sudachi tags typically mapped to universal or specific sets)
            # Placeholder for future spaCy integration
            pass
            
        return False

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
        
    def _load_ignored_vocabulary(self, lang_code: str) -> set:
        """Load all ignored (non-word) lemmas for a language into a fast lookup set."""
        words = self.db.get_all_ignored_words(lang_code)
        return {w['lemma'].lower() for w in words}

    def _is_punctuation(self, text: str) -> bool:
        """Check if token is purely punctuation or numbers."""
        # We want to ignore numbers as unknown words too
        return not any(c.isalpha() for c in text)
