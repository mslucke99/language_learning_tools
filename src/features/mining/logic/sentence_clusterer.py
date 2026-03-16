"""
Sentence Clusterer component for Context-Aware Sentence Mining.

Groups sentences by grammar patterns, topics, and difficulty levels using LLM analysis.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    """Result of sentence clustering."""
    sentence_id: int
    patterns: List[str]
    topics: List[str]
    collections_added: List[int]


class SentenceClusterer:
    """Clusters sentences by patterns, topics, and difficulty."""
    
    # Valid topic categories
    VALID_TOPICS = {
        'daily_life', 'business', 'technical', 'academic',
        'travel', 'culture', 'health', 'food'
    }
    
    # LLM prompts
    PATTERN_DETECTION_PROMPT = """Identify the main grammar patterns used in this {language} sentence.

Sentence: {sentence}

List the specific grammar patterns, constructions, or structures present. Examples might include:
- Conditional sentences (if-clauses)
- Subjunctive mood
- Passive voice
- Relative clauses
- Gerunds or infinitives
- Specific tenses (present perfect, past continuous, etc.)

Respond with a comma-separated list of pattern names, or "none" if no notable patterns."""
    
    TOPIC_DETECTION_PROMPT = """Classify this {language} sentence into one or more topic categories.

Sentence: {sentence}

Available categories:
- daily_life: everyday activities, routines, personal matters
- business: work, commerce, professional contexts
- technical: technology, science, specialized fields
- academic: education, research, scholarly topics
- travel: tourism, transportation, geography
- culture: arts, traditions, social customs
- health: medical, wellness, fitness
- food: cooking, dining, cuisine

Respond with a comma-separated list of applicable categories."""
    
    def __init__(self, db, llm_service=None):
        """
        Initialize clusterer with database and optional LLM service.
        
        Args:
            db: FlashcardDatabase instance
            llm_service: Optional LLMService instance for pattern/topic detection
        """
        self.db = db
        self.llm_service = llm_service
        self.pattern_cache = {}  # sentence_id -> patterns
        self.topic_cache = {}    # sentence_id -> topics
    
    def detect_grammar_patterns(self, sentence_id: int, timeout: int = 10) -> List[str]:
        """
        Detect grammar patterns in sentence using LLM.
        
        Args:
            sentence_id: ID of sentence to analyze
            timeout: Maximum seconds for LLM call
            
        Returns:
            List of detected grammar patterns
        """
        # Check cache first
        if sentence_id in self.pattern_cache:
            return self.pattern_cache[sentence_id]
        
        # Check database cache
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT detected_patterns FROM imported_content WHERE id = ?",
            (sentence_id,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:
            try:
                patterns = json.loads(row[0])
                self.pattern_cache[sentence_id] = patterns
                return patterns
            except json.JSONDecodeError:
                pass
        
        # If no LLM service, return empty list
        if not self.llm_service:
            return []
        
        try:
            # Get sentence text
            cursor.execute(
                "SELECT content, language FROM imported_content WHERE id = ?",
                (sentence_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return []
            
            sentence, language = row
            
            # Call LLM
            prompt = self.PATTERN_DETECTION_PROMPT.format(
                language=language,
                sentence=sentence
            )
            response = self.llm_service.generate_response(prompt, timeout=timeout)
            
            # Parse patterns
            patterns = [p.strip() for p in response.split(',') if p.strip() and p.strip().lower() != 'none']
            
            # Cache result
            cursor.execute(
                "UPDATE imported_content SET detected_patterns = ? WHERE id = ?",
                (json.dumps(patterns), sentence_id)
            )
            self.db.conn.commit()
            
            self.pattern_cache[sentence_id] = patterns
            return patterns
            
        except Exception as e:
            logger.warning(f'Pattern detection failed for sentence {sentence_id}: {e}')
            return []
    
    def detect_topics(self, sentence_id: int, timeout: int = 10) -> List[str]:
        """
        Detect topics in sentence using LLM.
        
        Args:
            sentence_id: ID of sentence to analyze
            timeout: Maximum seconds for LLM call
            
        Returns:
            List of topic categories
        """
        # Check cache first
        if sentence_id in self.topic_cache:
            return self.topic_cache[sentence_id]
        
        # Check database cache
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT detected_topics FROM imported_content WHERE id = ?",
            (sentence_id,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:
            try:
                topics = json.loads(row[0])
                self.topic_cache[sentence_id] = topics
                return topics
            except json.JSONDecodeError:
                pass
        
        # If no LLM service, return empty list
        if not self.llm_service:
            return []
        
        try:
            # Get sentence text
            cursor.execute(
                "SELECT content, language FROM imported_content WHERE id = ?",
                (sentence_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return []
            
            sentence, language = row
            
            # Call LLM
            prompt = self.TOPIC_DETECTION_PROMPT.format(
                language=language,
                sentence=sentence
            )
            response = self.llm_service.generate_response(prompt, timeout=timeout)
            
            # Parse and validate topics
            topics = [t.strip() for t in response.split(',')]
            valid_topics = [t for t in topics if t in self.VALID_TOPICS]
            
            # Default to daily_life if no valid topics
            if not valid_topics:
                valid_topics = ['daily_life']
            
            # Cache result
            cursor.execute(
                "UPDATE imported_content SET detected_topics = ? WHERE id = ?",
                (json.dumps(valid_topics), sentence_id)
            )
            self.db.conn.commit()
            
            self.topic_cache[sentence_id] = valid_topics
            return valid_topics
            
        except Exception as e:
            logger.warning(f'Topic detection failed for sentence {sentence_id}: {e}')
            return ['daily_life']  # Default fallback
    
    def create_pattern_collection(self, pattern: str, language: str) -> int:
        """
        Create or get collection for a grammar pattern.
        
        Args:
            pattern: Grammar pattern name
            language: Target language code
            
        Returns:
            Collection ID
        """
        cursor = self.db.conn.cursor()
        
        # Check if collection already exists
        cursor.execute("""
            SELECT id FROM sentence_collections
            WHERE collection_type = 'grammar_pattern' AND language = ? AND metadata LIKE ?
        """, (language, f'%"{pattern}"%'))
        
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Create new collection
        metadata = json.dumps({'pattern': pattern})
        cursor.execute("""
            INSERT INTO sentence_collections (name, description, collection_type, language, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f'{pattern} ({language})',
            f'Sentences with {pattern} grammar pattern',
            'grammar_pattern',
            language,
            metadata,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        self.db.conn.commit()
        
        return cursor.lastrowid
    
    def create_topic_collection(self, topic: str, language: str) -> int:
        """
        Create or get collection for a topic.
        
        Args:
            topic: Topic category name
            language: Target language code
            
        Returns:
            Collection ID
        """
        cursor = self.db.conn.cursor()
        
        # Check if collection already exists
        cursor.execute("""
            SELECT id FROM sentence_collections
            WHERE collection_type = 'topic' AND language = ? AND metadata LIKE ?
        """, (language, f'%"{topic}"%'))
        
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Create new collection
        metadata = json.dumps({'topic': topic})
        cursor.execute("""
            INSERT INTO sentence_collections (name, description, collection_type, language, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f'{topic.replace("_", " ").title()} ({language})',
            f'Sentences about {topic.replace("_", " ")}',
            'topic',
            language,
            metadata,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        self.db.conn.commit()
        
        return cursor.lastrowid
    
    def create_difficulty_ladder(self, base_sentence_id: int, language: str) -> Optional[int]:
        """
        Create a progressive difficulty ladder starting from base sentence.
        
        Args:
            base_sentence_id: Starting sentence ID
            language: Target language code
            
        Returns:
            Collection ID if ladder created, None if insufficient sentences
        """
        cursor = self.db.conn.cursor()
        
        # Get base sentence difficulty
        cursor.execute(
            "SELECT difficulty_score FROM imported_content WHERE id = ?",
            (base_sentence_id,)
        )
        row = cursor.fetchone()
        
        if not row or row[0] is None:
            return None
        
        base_difficulty = row[0]
        
        # Find related sentences with progressive difficulty
        cursor.execute("""
            SELECT id, difficulty_score FROM imported_content
            WHERE language = ? AND difficulty_score IS NOT NULL
            AND id != ?
            ORDER BY ABS(difficulty_score - ?) ASC
            LIMIT 20
        """, (language, base_sentence_id, base_difficulty))
        
        candidates = cursor.fetchall()
        
        # Build ladder with 0.05-0.15 step increases
        ladder_sentences = [(base_sentence_id, base_difficulty)]
        current_difficulty = base_difficulty
        
        for sentence_id, difficulty in candidates:
            if len(ladder_sentences) >= 10:
                break
            
            # Check if difficulty is in acceptable range (0.05-0.15 above current)
            if 0.05 <= (difficulty - current_difficulty) <= 0.15:
                ladder_sentences.append((sentence_id, difficulty))
                current_difficulty = difficulty
        
        # Need at least 5 sentences for a ladder
        if len(ladder_sentences) < 5:
            return None
        
        # Create collection
        metadata = json.dumps({
            'type': 'difficulty_ladder',
            'base_difficulty': base_difficulty,
            'step_count': len(ladder_sentences)
        })
        
        cursor.execute("""
            INSERT INTO sentence_collections (name, description, collection_type, language, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f'Difficulty Ladder {base_difficulty:.2f} ({language})',
            f'Progressive difficulty ladder starting at {base_difficulty:.2f}',
            'difficulty_ladder',
            language,
            metadata,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        collection_id = cursor.lastrowid
        
        # Add sentences to collection with sort order
        for sort_order, (sentence_id, _) in enumerate(ladder_sentences):
            cursor.execute("""
                INSERT INTO sentence_collection_items (collection_id, imported_content_id, sort_order, added_at)
                VALUES (?, ?, ?, ?)
            """, (collection_id, sentence_id, sort_order, datetime.now().isoformat()))
        
        self.db.conn.commit()
        
        return collection_id
    
    def auto_cluster_sentence(self, sentence_id: int):
        """
        Automatically detect patterns/topics and add to collections.
        
        Args:
            sentence_id: ID of sentence to cluster
        """
        try:
            # Get sentence language
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT language FROM imported_content WHERE id = ?",
                (sentence_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return
            
            language = row[0]
            
            # Detect patterns
            patterns = self.detect_grammar_patterns(sentence_id)
            for pattern in patterns:
                collection_id = self.create_pattern_collection(pattern, language)
                cursor.execute("""
                    INSERT OR IGNORE INTO sentence_collection_items (collection_id, imported_content_id, added_at)
                    VALUES (?, ?, ?)
                """, (collection_id, sentence_id, datetime.now().isoformat()))
            
            # Detect topics
            topics = self.detect_topics(sentence_id)
            for topic in topics:
                collection_id = self.create_topic_collection(topic, language)
                cursor.execute("""
                    INSERT OR IGNORE INTO sentence_collection_items (collection_id, imported_content_id, added_at)
                    VALUES (?, ?, ?)
                """, (collection_id, sentence_id, datetime.now().isoformat()))
            
            self.db.conn.commit()
            
        except Exception as e:
            logger.error(f'Error auto-clustering sentence {sentence_id}: {e}')
    
    def batch_cluster(self, sentence_ids: List[int], progress_callback=None) -> int:
        """
        Cluster multiple sentences in background.
        
        Args:
            sentence_ids: List of sentence IDs to cluster
            progress_callback: Optional callback(current, total)
            
        Returns:
            Number of sentences successfully clustered
        """
        success_count = 0
        total = len(sentence_ids)
        
        for i, sentence_id in enumerate(sentence_ids):
            try:
                self.auto_cluster_sentence(sentence_id)
                success_count += 1
            except Exception as e:
                logger.warning(f'Failed to cluster sentence {sentence_id}: {e}')
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, total)
        
        return success_count
    
    def link_to_grammar_book(self, pattern: str, language: str) -> Optional[int]:
        """
        Link pattern collection to existing grammar book entry if match found.
        
        Args:
            pattern: Grammar pattern name
            language: Target language code
            
        Returns:
            Grammar book entry ID if linked, None otherwise
        """
        cursor = self.db.conn.cursor()
        
        # Search for matching grammar book entry
        cursor.execute("""
            SELECT id FROM grammar_book_entries
            WHERE language = ? AND (title LIKE ? OR tags LIKE ?)
            LIMIT 1
        """, (language, f'%{pattern}%', f'%{pattern}%'))
        
        row = cursor.fetchone()
        return row[0] if row else None
