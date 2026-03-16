"""
Sentence Recommender component for Context-Aware Sentence Mining.

Generates personalized sentence recommendations based on user's current level
and learning history using comprehensible input theory (i+1 level).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RecommendedSentence:
    """Recommended sentence with metadata."""
    sentence_id: int
    content: str
    difficulty_score: float
    reason: str
    unknown_word_count: int


class SentenceRecommender:
    """Generates personalized sentence recommendations."""
    
    def __init__(self, db):
        """
        Initialize recommender with database access.
        
        Args:
            db: FlashcardDatabase instance
        """
        self.db = db
    
    def calculate_user_level(self, language: str, lookback_days: int = 30) -> float:
        """
        Calculate user's current difficulty level from recent study history.
        
        Args:
            language: Target language code
            lookback_days: Number of days to analyze
            
        Returns:
            Average difficulty score (0.0-1.0) of recently studied sentences
        """
        cursor = self.db.conn.cursor()
        
        # Get sentences studied in the lookback period
        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        
        cursor.execute("""
            SELECT AVG(ic.difficulty_score)
            FROM sentence_study_progress ssp
            JOIN imported_content ic ON ssp.imported_content_id = ic.id
            WHERE ic.language = ? AND ssp.last_reviewed >= ?
            AND ic.difficulty_score IS NOT NULL
        """, (language, cutoff_date))
        
        row = cursor.fetchone()
        
        if row and row[0] is not None:
            return row[0]
        
        # If no recent reviews, return beginner level
        return 0.2
    
    def find_i_plus_one_sentences(self, current_level: float, language: str, 
                                   count: int = 10) -> List[int]:
        """
        Find sentences at i+1 level (0.1-0.2 above current level).
        
        Args:
            current_level: User's current difficulty level
            language: Target language code
            count: Maximum sentences to return
            
        Returns:
            List of sentence IDs at appropriate difficulty
        """
        cursor = self.db.conn.cursor()
        
        # i+1 level is 0.1-0.2 above current level
        min_difficulty = current_level + 0.1
        max_difficulty = current_level + 0.2
        
        cursor.execute("""
            SELECT id FROM imported_content
            WHERE language = ? 
            AND content_type = 'sentence'
            AND difficulty_score IS NOT NULL
            AND difficulty_score >= ? 
            AND difficulty_score <= ?
            ORDER BY difficulty_score ASC
            LIMIT ?
        """, (language, min_difficulty, max_difficulty, count))
        
        return [row[0] for row in cursor.fetchall()]
    
    def find_similar_sentences(self, sentence_id: int, count: int = 5) -> List[int]:
        """
        Find sentences similar to the given sentence.
        
        Uses difficulty score, shared collections, and topic similarity.
        
        Args:
            sentence_id: Reference sentence ID
            count: Number of similar sentences to return
            
        Returns:
            List of similar sentence IDs
        """
        cursor = self.db.conn.cursor()
        
        # Get reference sentence info
        cursor.execute("""
            SELECT difficulty_score, language, detected_topics
            FROM imported_content
            WHERE id = ?
        """, (sentence_id,))
        
        row = cursor.fetchone()
        if not row:
            return []
        
        ref_difficulty, language, ref_topics_json = row
        
        if not ref_difficulty:
            return []
        
        # Find sentences with similar difficulty (within 0.15 points)
        cursor.execute("""
            SELECT id, difficulty_score, detected_topics
            FROM imported_content
            WHERE language = ?
            AND content_type = 'sentence'
            AND id != ?
            AND difficulty_score IS NOT NULL
            AND ABS(difficulty_score - ?) <= 0.15
            ORDER BY ABS(difficulty_score - ?) ASC
            LIMIT ?
        """, (language, sentence_id, ref_difficulty, ref_difficulty, count * 2))
        
        candidates = cursor.fetchall()
        
        # Score candidates by topic overlap
        import json
        try:
            ref_topics = set(json.loads(ref_topics_json)) if ref_topics_json else set()
        except (json.JSONDecodeError, TypeError):
            ref_topics = set()
        
        scored_candidates = []
        for cand_id, cand_difficulty, cand_topics_json in candidates:
            try:
                cand_topics = set(json.loads(cand_topics_json)) if cand_topics_json else set()
            except (json.JSONDecodeError, TypeError):
                cand_topics = set()
            
            # Calculate similarity score
            topic_overlap = len(ref_topics & cand_topics)
            difficulty_proximity = 1.0 - abs(cand_difficulty - ref_difficulty) / 0.15
            
            similarity_score = (topic_overlap * 0.5) + (difficulty_proximity * 0.5)
            scored_candidates.append((cand_id, similarity_score))
        
        # Sort by similarity and return top count
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return [cand_id for cand_id, _ in scored_candidates[:count]]
    
    def _exclude_recently_studied(self, sentence_ids: List[int], 
                                   language: str, days: int = 7) -> List[int]:
        """Filter out sentences studied within the specified days."""
        if not sentence_ids:
            return []
        
        cursor = self.db.conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get recently studied sentence IDs
        placeholders = ','.join('?' * len(sentence_ids))
        cursor.execute(f"""
            SELECT DISTINCT imported_content_id
            FROM sentence_study_progress
            WHERE imported_content_id IN ({placeholders})
            AND last_reviewed >= ?
        """, sentence_ids + [cutoff_date])
        
        recently_studied = {row[0] for row in cursor.fetchall()}
        
        # Return sentences not in recently studied set
        return [sid for sid in sentence_ids if sid not in recently_studied]
    
    def get_recommendations(self, language: str, count: int = 5) -> List[RecommendedSentence]:
        """
        Generate personalized sentence recommendations.
        
        Args:
            language: Target language code
            count: Number of recommendations to return
            
        Returns:
            List of recommended sentences with metadata
        """
        try:
            # Calculate user's current level
            current_level = self.calculate_user_level(language)
            
            # Find i+1 level sentences
            i_plus_one_ids = self.find_i_plus_one_sentences(current_level, language, count * 2)
            
            # Exclude recently studied
            filtered_ids = self._exclude_recently_studied(i_plus_one_ids, language)
            
            # Get sentence details
            cursor = self.db.conn.cursor()
            recommendations = []
            
            for sentence_id in filtered_ids[:count]:
                cursor.execute("""
                    SELECT content, difficulty_score, unknown_words
                    FROM imported_content
                    WHERE id = ?
                """, (sentence_id,))
                
                row = cursor.fetchone()
                if row:
                    content, difficulty, unknown_words_json = row
                    
                    import json
                    try:
                        unknown_words = json.loads(unknown_words_json) if unknown_words_json else []
                    except (json.JSONDecodeError, TypeError):
                        unknown_words = []
                    
                    recommendations.append(RecommendedSentence(
                        sentence_id=sentence_id,
                        content=content,
                        difficulty_score=difficulty,
                        reason=f"i+1 level (current: {current_level:.2f})",
                        unknown_word_count=len(unknown_words)
                    ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f'Error generating recommendations: {e}')
            return []
