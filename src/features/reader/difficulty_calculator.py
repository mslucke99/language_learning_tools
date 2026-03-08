"""
Difficulty calculator for Immersive Reading Mode.

Calculates difficulty scores for reading content based on vocabulary complexity,
sentence length, and grammatical complexity.
"""

import re
from typing import Dict, List, Tuple
from collections import Counter


class DifficultyCalculator:
    """
    Calculates difficulty scores for reading content.
    
    Difficulty score ranges from 0.0 (easiest) to 1.0 (hardest).
    Difficulty ratings: 'easy' (0.0-0.33), 'medium' (0.33-0.67), 'hard' (0.67-1.0)
    
    Factors considered:
    - Vocabulary complexity (word length, unique word ratio)
    - Sentence length (average words per sentence)
    - Grammatical complexity (sentence structure indicators)
    """
    
    # Difficulty rating thresholds
    EASY_THRESHOLD = 0.33
    MEDIUM_THRESHOLD = 0.67
    
    # Scoring weights
    VOCAB_WEIGHT = 0.5
    SENTENCE_LENGTH_WEIGHT = 0.3
    GRAMMAR_WEIGHT = 0.2
    
    # Reference values for normalization
    # These are approximate values based on language learning research
    AVG_WORD_LENGTH_EASY = 4.0  # Average characters per word for easy text
    AVG_WORD_LENGTH_HARD = 8.0  # Average characters per word for hard text
    
    AVG_SENTENCE_LENGTH_EASY = 8.0  # Average words per sentence for easy text
    AVG_SENTENCE_LENGTH_HARD = 25.0  # Average words per sentence for hard text
    
    UNIQUE_RATIO_EASY = 0.4  # Low vocabulary diversity (easier)
    UNIQUE_RATIO_HARD = 0.8  # High vocabulary diversity (harder)
    
    def __init__(self):
        """Initialize the DifficultyCalculator."""
        pass
    
    def calculate_difficulty(self, content: str, language: str = 'en') -> Dict:
        """
        Calculate difficulty score for content.
        
        Args:
            content: Text content to analyze
            language: Language code (currently not used, reserved for future)
            
        Returns:
            Dictionary containing:
            - difficulty_score: Float from 0.0 to 1.0
            - difficulty_rating: 'easy', 'medium', or 'hard'
            - vocab_score: Vocabulary complexity score
            - sentence_length_score: Sentence length score
            - grammar_score: Grammatical complexity score
            - metrics: Dictionary of raw metrics used in calculation
        """
        # Parse content into words and sentences
        words = self._extract_words(content)
        sentences = self._extract_sentences(content)
        
        # Handle edge cases
        if not words or not sentences:
            return {
                'difficulty_score': 0.0,
                'difficulty_rating': 'easy',
                'vocab_score': 0.0,
                'sentence_length_score': 0.0,
                'grammar_score': 0.0,
                'metrics': {}
            }
        
        # Calculate component scores
        vocab_score = self._calculate_vocab_complexity(words)
        sentence_length_score = self._calculate_sentence_length_complexity(words, sentences)
        grammar_score = self._calculate_grammar_complexity(sentences)
        
        # Calculate weighted overall difficulty score
        difficulty_score = (
            vocab_score * self.VOCAB_WEIGHT +
            sentence_length_score * self.SENTENCE_LENGTH_WEIGHT +
            grammar_score * self.GRAMMAR_WEIGHT
        )
        
        # Clamp to [0.0, 1.0] range
        difficulty_score = max(0.0, min(1.0, difficulty_score))
        
        # Assign difficulty rating
        difficulty_rating = self._assign_rating(difficulty_score)
        
        # Collect metrics for transparency
        metrics = {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'unique_word_count': len(set(w.lower() for w in words)),
            'avg_word_length': sum(len(w) for w in words) / len(words),
            'avg_sentence_length': len(words) / len(sentences),
            'unique_word_ratio': len(set(w.lower() for w in words)) / len(words)
        }
        
        return {
            'difficulty_score': round(difficulty_score, 3),
            'difficulty_rating': difficulty_rating,
            'vocab_score': round(vocab_score, 3),
            'sentence_length_score': round(sentence_length_score, 3),
            'grammar_score': round(grammar_score, 3),
            'metrics': metrics
        }
    
    def _extract_words(self, text: str) -> List[str]:
        """
        Extract words from text.
        
        Args:
            text: Text content
            
        Returns:
            List of words (excluding punctuation)
        """
        # Remove punctuation and split on whitespace
        # Keep apostrophes for contractions (don't, it's, etc.)
        words = re.findall(r"\b[\w']+\b", text, re.UNICODE)
        return [w for w in words if w.strip()]
    
    def _extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text.
        
        Args:
            text: Text content
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting on common sentence endings
        # Handles periods, question marks, exclamation marks
        sentences = re.split(r'[.!?。！？]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_vocab_complexity(self, words: List[str]) -> float:
        """
        Calculate vocabulary complexity score.
        
        Considers:
        - Average word length (longer words = harder)
        - Unique word ratio (more diverse vocabulary = harder)
        
        Args:
            words: List of words
            
        Returns:
            Score from 0.0 to 1.0
        """
        if not words:
            return 0.0
        
        # Calculate average word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Normalize to 0-1 scale
        word_length_score = (avg_word_length - self.AVG_WORD_LENGTH_EASY) / \
                           (self.AVG_WORD_LENGTH_HARD - self.AVG_WORD_LENGTH_EASY)
        word_length_score = max(0.0, min(1.0, word_length_score))
        
        # Calculate unique word ratio (vocabulary diversity)
        unique_words = set(w.lower() for w in words)
        unique_ratio = len(unique_words) / len(words)
        
        # Normalize to 0-1 scale
        diversity_score = (unique_ratio - self.UNIQUE_RATIO_EASY) / \
                         (self.UNIQUE_RATIO_HARD - self.UNIQUE_RATIO_EASY)
        diversity_score = max(0.0, min(1.0, diversity_score))
        
        # Average the two components
        vocab_score = (word_length_score + diversity_score) / 2.0
        
        return vocab_score
    
    def _calculate_sentence_length_complexity(
        self, 
        words: List[str], 
        sentences: List[str]
    ) -> float:
        """
        Calculate sentence length complexity score.
        
        Longer sentences are generally harder to parse and understand.
        
        Args:
            words: List of words
            sentences: List of sentences
            
        Returns:
            Score from 0.0 to 1.0
        """
        if not sentences:
            return 0.0
        
        # Calculate average sentence length in words
        avg_sentence_length = len(words) / len(sentences)
        
        # Normalize to 0-1 scale
        length_score = (avg_sentence_length - self.AVG_SENTENCE_LENGTH_EASY) / \
                      (self.AVG_SENTENCE_LENGTH_HARD - self.AVG_SENTENCE_LENGTH_EASY)
        length_score = max(0.0, min(1.0, length_score))
        
        return length_score
    
    def _calculate_grammar_complexity(self, sentences: List[str]) -> float:
        """
        Calculate grammatical complexity score.
        
        Looks for indicators of complex grammar:
        - Subordinate clauses (which, that, who, when, where, etc.)
        - Conjunctions (and, but, or, because, although, etc.)
        - Passive voice indicators (was, were, been, being + past participle)
        - Relative pronouns
        
        Args:
            sentences: List of sentences
            
        Returns:
            Score from 0.0 to 1.0
        """
        if not sentences:
            return 0.0
        
        # Complexity indicators (case-insensitive)
        subordinate_markers = [
            'which', 'that', 'who', 'whom', 'whose', 'when', 'where', 'why',
            'because', 'although', 'though', 'while', 'if', 'unless', 'until',
            'since', 'whereas', 'whether'
        ]
        
        # Count complexity indicators across all sentences
        total_indicators = 0
        total_words = 0
        
        for sentence in sentences:
            words = self._extract_words(sentence.lower())
            total_words += len(words)
            
            # Count subordinate markers
            for marker in subordinate_markers:
                total_indicators += words.count(marker)
            
            # Count commas (often indicate complex sentence structure)
            total_indicators += sentence.count(',') * 0.5  # Weight commas less
        
        # Calculate indicator density
        if total_words == 0:
            return 0.0
        
        indicator_density = total_indicators / total_words
        
        # Normalize to 0-1 scale
        # Assume 0.1 indicators per word is high complexity
        grammar_score = indicator_density / 0.1
        grammar_score = max(0.0, min(1.0, grammar_score))
        
        return grammar_score
    
    def _assign_rating(self, difficulty_score: float) -> str:
        """
        Assign difficulty rating based on score.
        
        Args:
            difficulty_score: Score from 0.0 to 1.0
            
        Returns:
            'easy', 'medium', or 'hard'
        """
        if difficulty_score < self.EASY_THRESHOLD:
            return 'easy'
        elif difficulty_score < self.MEDIUM_THRESHOLD:
            return 'medium'
        else:
            return 'hard'
