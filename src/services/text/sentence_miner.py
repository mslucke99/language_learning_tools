import re
import unicodedata
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from src.core.database import FlashcardDatabase
from src.services.text.tokenizer_service import TokenizerService, Token
from src.services.dictionary.dictionary_manager import DictionaryEngine
from src.services.text.grammar_extractor import GrammarExtractor
import regex

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
        Robust sentence splitting for multiple languages using Unicode-aware boundaries.
        
        Handles:
        - Multiple languages including English, Chinese, Korean, Japanese, and European languages
        - Proper newline handling (blank lines always break, single newlines depend on context)
        - Simple abbreviations in English (Dr., Mr., Jan., etc.)
        - Decimals and numbers (protected from false splits via negative lookbehind)
        - CJK punctuation (。！？) which are unambiguous sentence terminators
        
        Known Limitations (edge cases to improve later):
        - Complex multi-period abbreviations like "U.S.A.", "e.g.", "i.e." may split incorrectly
        - Short fragments (1-2 chars ending with period from such abbreviations may merge incorrectly
        - Dates in format YYYY.MM.DD may be affected by the digit lookbehind
        - Some edge cases with mixed punctuation may produce unexpected results
        - Very short texts without clear sentence boundaries may not split as expected
        
        Newline rules:
        - Blank lines (2+ newlines) always separate paragraphs.
        - A single newline is treated as a sentence boundary only if the previous
          line ends with a terminator and the next line starts with a letter.
        - Otherwise, single-newline breaks are merged as word-wrap.

        Inline terminator splitting:
        - ASCII terminators (.!?) split only when followed by whitespace + a
          sentence-starting letter or end-of-text.
        - Periods after digits are protected to avoid splitting decimals/dates.
        - CJK terminators (。！？) always split because they are unambiguous.
        - Simple abbreviations like Dr., Mr., Jan. are merged back after splitting.
        """
        if not text:
            return []
            
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split into paragraphs on blank lines (always a boundary)
        paragraphs = re.split(r'\n{2,}', text)
        
        raw_sentences = []
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            # Process each paragraph
            para_sentences = self._split_paragraph(para)
            raw_sentences.extend(para_sentences)
            
        # Filter out empty sentences and strip whitespace
        return [s.strip() for s in raw_sentences if s.strip()]

    def _split_paragraph(self, paragraph: str) -> List[str]:
        """Split a single paragraph into sentences."""
        # Define sentence terminators for different language blocks
        # Western: . ! ?
        # Chinese/Japanese: 。 ！ ？
        # Korean: 。 ！ ？ (though Korean often uses Western punctuation too)
        SENTENCE_TERMINATORS = '.!?。！？'
        
        # Unicode property escapes for regex
        # \p{L} = any letter
        # \p{Nl} = letter-like numerals (like Roman numerals)
        # \p{Pe}, \p{Pf} = close/open punctuation
        # \p{Pi}, \p{Ps} = initial/final quote punctuation
        # \p{Zs} = space separator
        # \p{Zl} = line separator
        # \p{Zp} = paragraph separator
        
        SENTENCE_STARTER = r'[\p{L}\p{Nl}]'  # Letters or letter-like numbers
        SENTENCE_OPENERS = r'["\'\(\[\p{Pi}\p{Ps}]*'  # Opening quotes/brackets
        SENTENCE_ENDERS = r'[\p{Pe}\p{Pf}"\']*'  # Closing quotes/brackets
        
        # Pattern to detect where sentences end
        ENDS_SENTENCE_RE = regex.compile(
            r'[' + regex.escape(SENTENCE_TERMINATORS) + r']' + SENTENCE_ENDERS + r'\s*$'
        )
        
        # Pattern to detect where sentences start (after potential whitespace/openers)
        STARTS_NEW_SENTENCE_RE = regex.compile(
            r'^\s*' + SENTENCE_OPENERS + SENTENCE_STARTER
        )
        
        # Common abbreviations that shouldn't trigger sentence splits
        ABBREV_RE = regex.compile(
            r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|approx|dept|est|vol|pp|fig|'
            r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
            r'Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?',
            regex.IGNORECASE
        )
        
        # --- Step 1: Handle explicit line breaks ---
        lines = [ln.strip() for ln in paragraph.split('\n') if ln.strip()]
        if not lines:
            return []
            
        # Merge lines that are likely word-wrapped rather than sentence breaks
        merged_lines = []
        current_line = lines[0]
        
        for i in range(1, len(lines)):
            next_line = lines[i]
            # Check if current line ends with sentence terminator and next line starts with sentence starter
            ends_with_terminator = bool(ENDS_SENTENCE_RE.search(current_line))
            starts_with_starter = bool(STARTS_NEW_SENTENCE_RE.search(next_line))
            
            if ends_with_terminator and starts_with_starter:
                # This is likely a real sentence break
                merged_lines.append(current_line)
                current_line = next_line
            else:
                # This is likely word-wrapping, merge with space
                current_line = current_line + ' ' + next_line
                
        merged_lines.append(current_line)
        
            # --- Step 2: Split each merged line on inline terminators ---
        all_candidates = []
        
        for block in merged_lines:
            if not any(c in block for c in SENTENCE_TERMINATORS):
                # No terminators, treat as one sentence
                all_candidates.append(block)
                continue
                
            # Split on sentence terminators
            # We want to split on:
            # 1. Western terminators (.!?) when followed by whitespace + sentence starter OR end of text
            # 2. CJK terminators (。！？) always (they're unambiguous)
            # But protect against splits after digits (decimals, etc.)
            
            # Pattern explanation:
            # (?<!\d) - not preceded by digit (protect decimals)
            # ([.!?][\p{Pe}\p{Pf}"\']*) - Western terminator with optional closing punctuation
            # (?=\s*(?:' + SENTENCE_OPENERS + SENTENCE_STARTER + r')|\s*$) - followed by optional whitespace + opener+starter OR end
            # | - OR
            # ([。！？]) - CJK terminator (always split)
            SPLIT_PATTERN = regex.compile(
                r'(?<!\d)([.!?][\p{Pe}\p{Pf}"\']*)(?=\s*(?:' + SENTENCE_OPENERS + SENTENCE_STARTER + r')|\s*$)' +
                r'|([。！？])'
            )
            
            # Find all matches and their positions
            matches = list(SPLIT_PATTERN.finditer(block))
            if not matches:
                # No matches, treat as one sentence
                all_candidates.append(block)
                continue
                
            # Split the block based on match positions
            candidates = []
            start = 0
            for match in matches:
                # Add text before the match
                if start < match.start():
                    sentence_part = block[start:match.start()].strip()
                    if sentence_part:
                        candidates.append(sentence_part)
                
                # Add the matched delimiter (the terminator)
                sentence_part = match.group(0).strip()
                if sentence_part:
                    candidates.append(sentence_part)
                    
                start = match.end()
            
            # Add remaining text after last match
            if start < len(block):
                sentence_part = block[start:].strip()
                if sentence_part:
                    candidates.append(sentence_part)
            
            # Now we need to merge text parts with their following delimiters
            # Since we split on delimiters, the pattern is: [text, delimiter, text, delimiter, ...]
            # We want to merge each text with its following delimiter
            merged_candidates = []
            i = 0
            while i < len(candidates):
                text_part = candidates[i]
                # Check if next item is a delimiter (punctuation)
                if i + 1 < len(candidates) and regex.match(r'^[.!?。！？]+[\p{Pe}\p{Pf}"\']*$', candidates[i + 1]):
                    # Merge text with its delimiter
                    merged = (text_part + candidates[i + 1]).strip()
                    if merged:
                        merged_candidates.append(merged)
                    i += 2  # Skip both text and delimiter
                else:
                    # No following delimiter, just add the text part
                    if text_part:
                        merged_candidates.append(text_part)
                    i += 1
            
            all_candidates.extend(merged_candidates)
            
        # --- Step 3: Merge back abbreviations and very short fragments that were incorrectly split ---
        final_sentences = []
        i = 0
        while i < len(all_candidates):
            candidate = all_candidates[i]
            
            # Check if this ends with an abbreviation and there's a next candidate
            is_abbreviation = (i + 1 < len(all_candidates) and 
                              ABBREV_RE.search(candidate) and 
                              not candidate.endswith('..'))  # Avoid double dots
            
            # Also check if this is a very short fragment (likely part of abbreviated text like "U.", "S.", etc.)
            # Very short fragments ending with period are often incorrectly split abbreviations
            is_short_fragment = (len(candidate.strip()) <= 2 and 
                                candidate.strip().endswith('.') and
                                i + 1 < len(all_candidates))
            
            if is_abbreviation or is_short_fragment:
                # Merge with next candidate
                merged = candidate + ' ' + all_candidates[i + 1]
                final_sentences.append(merged)
                i += 2  # Skip both current and next items as they've been merged
            else:
                final_sentences.append(candidate)
                i += 1  # Move to next item
                
        return final_sentences

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
