"""
Sentence Analyzer component for Context-Aware Sentence Mining.

Analyzes sentences for difficulty by combining vocabulary analysis and
LLM-powered grammar complexity detection.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DifficultyResult:
    """Result of sentence difficulty analysis."""
    difficulty_score: float
    known_word_ratio: float
    grammar_complexity: str
    unknown_words: List[str]
    rare_word_count: int


class SentenceAnalyzer:
    """Analyzes sentence difficulty using vocabulary and grammar analysis."""
    
    # Grammar complexity weights
    GRAMMAR_WEIGHTS = {
        'beginner': 0.2,
        'intermediate': 0.5,
        'advanced': 0.8
    }
    
    # Difficulty classification thresholds
    DIFFICULTY_THRESHOLDS = {
        'easy': (0.0, 0.33),
        'medium': (0.34, 0.66),
        'hard': (0.67, 1.0)
    }
    
    # LLM prompts
    GRAMMAR_COMPLEXITY_PROMPT = """Analyze the grammatical complexity of this {language} sentence and classify it as beginner, intermediate, or advanced.

Sentence: {sentence}

Consider:
- Verb tenses and moods used
- Sentence structure complexity
- Use of subordinate clauses
- Idiomatic expressions
- Advanced grammatical constructions

Respond with ONLY one word: beginner, intermediate, or advanced."""
    
    def __init__(self, db, llm_service=None):
        """
        Initialize analyzer with database and optional LLM service.
        
        Args:
            db: FlashcardDatabase instance
            llm_service: Optional LLMService instance for grammar analysis
        """
        self.db = db
        self.llm_service = llm_service
        self.frequency_lists = {}  # language -> set of common words
        self.user_vocabulary_cache = {}  # language -> set of known words
        self._load_frequency_lists()
    
    def _load_frequency_lists(self):
        """Load frequency lists for supported languages into memory."""
        supported_languages = ['spanish', 'korean', 'japanese', 'french', 'german', 'chinese']
        resources_dir = Path(__file__).parent.parent.parent.parent / 'resources' / 'frequency_lists'
        
        for lang in supported_languages:
            file_path = resources_dir / f'{lang}_10k.json'
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        words = json.load(f)
                        # Store as set for O(1) lookup
                        self.frequency_lists[lang] = set(words[:5000])  # Top 5000 for rare word detection
                        logger.info(f'Loaded frequency list for {lang}: {len(self.frequency_lists[lang])} words')
                except Exception as e:
                    logger.warning(f'Failed to load frequency list for {lang}: {e}')
    
    def _get_user_vocabulary(self, language: str) -> set:
        """
        Get user's known vocabulary from flashcards and known_words table.
        
        Args:
            language: Target language code
            
        Returns:
            Set of known words
        """
        # Check cache first
        if language in self.user_vocabulary_cache:
            return self.user_vocabulary_cache[language]
        
        known_words = set()
        
        try:
            # Get words from flashcards
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT LOWER(question) FROM flashcards
                WHERE deck_id IN (SELECT id FROM decks WHERE language = ?)
            """, (language,))
            for row in cursor.fetchall():
                if row[0]:
                    known_words.add(row[0])
            
            # Get words from known_words table
            cursor.execute("""
                SELECT DISTINCT LOWER(lemma) FROM known_words
                WHERE language = ? AND is_ignored = 0
            """, (language,))
            for row in cursor.fetchall():
                if row[0]:
                    known_words.add(row[0])
            
            # Cache the result
            self.user_vocabulary_cache[language] = known_words
            logger.debug(f'Loaded {len(known_words)} known words for {language}')
            
        except Exception as e:
            logger.warning(f'Error loading user vocabulary for {language}: {e}')
        
        return known_words
    
    def _tokenize_sentence(self, sentence: str, language: str) -> List[str]:
        """
        Tokenize sentence into words.
        
        Args:
            sentence: Sentence text
            language: Target language code
            
        Returns:
            List of words
        """
        # Simple tokenization - split on whitespace and punctuation
        # For production, would use language-specific tokenizers (spacy, konlpy, etc.)
        words = re.findall(r'\b\w+\b', sentence.lower())
        return words
    
    def calculate_known_word_ratio(self, sentence: str, language: str) -> Tuple[float, List[str]]:
        """
        Calculate percentage of known words and identify unknown words.
        
        Args:
            sentence: The sentence text
            language: Target language code
            
        Returns:
            Tuple of (ratio 0.0-1.0, list of unknown words)
        """
        words = self._tokenize_sentence(sentence, language)
        if not words:
            return 1.0, []
        
        known_vocab = self._get_user_vocabulary(language)
        unknown_words = []
        known_count = 0
        
        for word in words:
            if word in known_vocab:
                known_count += 1
            else:
                unknown_words.append(word)
        
        ratio = known_count / len(words) if words else 1.0
        return ratio, unknown_words
    
    def _check_rare_words(self, words: List[str], language: str) -> int:
        """
        Count words not in top 5000 frequency list.
        
        Args:
            words: List of words to check
            language: Target language code
            
        Returns:
            Count of rare words
        """
        if language not in self.frequency_lists:
            return 0
        
        frequency_set = self.frequency_lists[language]
        rare_count = 0
        
        for word in words:
            if word.lower() not in frequency_set:
                rare_count += 1
        
        return rare_count
    
    def detect_grammar_complexity(self, sentence: str, language: str, timeout: int = 10) -> str:
        """
        Use LLM to classify grammar complexity.
        
        Args:
            sentence: The sentence text
            language: Target language code
            timeout: Maximum seconds for LLM call
            
        Returns:
            One of: "beginner", "intermediate", "advanced"
            
        Raises:
            TimeoutError: If LLM call exceeds timeout
        """
        if not self.llm_service:
            # Fallback to vocabulary-based estimation
            return self._estimate_complexity_from_vocabulary(sentence, language)
        
        try:
            prompt = self.GRAMMAR_COMPLEXITY_PROMPT.format(
                language=language,
                sentence=sentence
            )
            
            response = self.llm_service.generate_response(prompt, timeout=timeout)
            complexity = response.strip().lower()
            
            # Validate response
            if complexity in self.GRAMMAR_WEIGHTS:
                return complexity
            
            # Fallback if response unclear
            logger.warning(f'Unexpected LLM response for grammar complexity: {response}')
            return 'intermediate'
            
        except TimeoutError:
            logger.warning(f'Grammar complexity detection timeout for sentence: {sentence[:50]}...')
            return self._estimate_complexity_from_vocabulary(sentence, language)
        except Exception as e:
            logger.warning(f'Grammar complexity detection failed: {e}')
            return self._estimate_complexity_from_vocabulary(sentence, language)
    
    def _estimate_complexity_from_vocabulary(self, sentence: str, language: str) -> str:
        """
        Estimate grammar complexity from vocabulary when LLM is unavailable.
        
        Args:
            sentence: The sentence text
            language: Target language code
            
        Returns:
            Estimated complexity level
        """
        # Simple heuristics: sentence length and punctuation
        words = self._tokenize_sentence(sentence, language)
        word_count = len(words)
        
        # Check for complex structures
        has_subordinate = any(word in sentence.lower() for word in ['que', 'si', 'porque', 'aunque', 'cuando', 'donde'])
        has_multiple_verbs = sentence.count('é') + sentence.count('á') + sentence.count('í') > 2
        
        if word_count > 20 or (has_subordinate and has_multiple_verbs):
            return 'advanced'
        elif word_count > 12 or has_subordinate:
            return 'intermediate'
        else:
            return 'beginner'
    
    def calculate_difficulty_score(self, known_word_ratio: float, grammar_complexity: str) -> float:
        """
        Combine metrics into final difficulty score.
        
        Formula: (1 - known_word_ratio) * 0.6 + grammar_weight * 0.4
        
        Args:
            known_word_ratio: Percentage of known words (0.0-1.0)
            grammar_complexity: Grammar level classification
            
        Returns:
            Difficulty score (0.0-1.0)
        """
        grammar_weight = self.GRAMMAR_WEIGHTS.get(grammar_complexity, 0.5)
        
        # Vocabulary contributes 60%, grammar contributes 40%
        score = (1 - known_word_ratio) * 0.6 + grammar_weight * 0.4
        
        # Clamp to 0.0-1.0 range
        return max(0.0, min(1.0, score))
    
    def classify_difficulty(self, score: float) -> str:
        """
        Classify difficulty score into category.
        
        Args:
            score: Difficulty score (0.0-1.0)
            
        Returns:
            One of: "easy", "medium", "hard"
        """
        if score <= 0.33:
            return 'easy'
        elif score <= 0.66:
            return 'medium'
        else:
            return 'hard'
    
    def analyze_sentence(self, sentence_id: int, timeout: int = 10) -> DifficultyResult:
        """
        Analyze a single sentence and return difficulty metrics.
        
        Args:
            sentence_id: ID of sentence in imported_content table
            timeout: Maximum seconds for LLM analysis
            
        Returns:
            DifficultyResult with score, known_word_ratio, grammar_complexity, unknown_words
            
        Raises:
            TimeoutError: If analysis exceeds timeout
            Exception: If sentence not found
        """
        try:
            # Get sentence from database
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT content, language FROM imported_content WHERE id = ?",
                (sentence_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f'Sentence {sentence_id} not found')
            
            sentence, language = row
            
            # Calculate known word ratio
            known_word_ratio, unknown_words = self.calculate_known_word_ratio(sentence, language)
            
            # Detect grammar complexity
            grammar_complexity = self.detect_grammar_complexity(sentence, language, timeout)
            
            # Calculate difficulty score
            difficulty_score = self.calculate_difficulty_score(known_word_ratio, grammar_complexity)
            
            # Check for rare words
            words = self._tokenize_sentence(sentence, language)
            rare_word_count = self._check_rare_words(words, language)
            
            # Store results in database
            cursor.execute("""
                UPDATE imported_content
                SET difficulty_score = ?, known_word_ratio = ?, grammar_complexity = ?,
                    unknown_words = ?, detected_patterns = ?, analysis_timestamp = ?
                WHERE id = ?
            """, (
                difficulty_score,
                known_word_ratio,
                grammar_complexity,
                json.dumps(unknown_words),
                json.dumps([]),  # patterns will be filled by clusterer
                datetime.now().isoformat(),
                sentence_id
            ))
            self.db.conn.commit()
            
            return DifficultyResult(
                difficulty_score=difficulty_score,
                known_word_ratio=known_word_ratio,
                grammar_complexity=grammar_complexity,
                unknown_words=unknown_words,
                rare_word_count=rare_word_count
            )
            
        except Exception as e:
            logger.error(f'Error analyzing sentence {sentence_id}: {e}')
            raise
    
    def batch_analyze(self, sentence_ids: List[int], progress_callback=None) -> int:
        """
        Queue multiple sentences for analysis.
        
        Args:
            sentence_ids: List of sentence IDs to analyze
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            Number of sentences successfully analyzed
        """
        success_count = 0
        total = len(sentence_ids)
        
        for i, sentence_id in enumerate(sentence_ids):
            try:
                self.analyze_sentence(sentence_id)
                success_count += 1
            except Exception as e:
                logger.warning(f'Failed to analyze sentence {sentence_id}: {e}')
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, total)
        
        return success_count
