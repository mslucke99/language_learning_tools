"""Definition caching system for reading mode.

This module provides caching functionality for word definitions to improve
performance and reduce LLM API calls during reading sessions.
"""

import hashlib
from datetime import datetime
from typing import Optional, Dict
from src.core.database import FlashcardDatabase


class DefinitionCache:
    """Manages caching of word definitions for reading mode.
    
    The cache stores definitions with context-specific hashes to provide
    contextual definitions. It also tracks access patterns for cache
    management and analytics.
    """
    
    def __init__(self, db: FlashcardDatabase):
        """Initialize the definition cache.
        
        Args:
            db: FlashcardDatabase instance for storage
        """
        self.db = db
    
    def get_definition(
        self,
        word: str,
        language: str,
        context: str
    ) -> Optional[Dict]:
        """Get a cached definition for a word.
        
        Checks context-specific cache first, then falls back to generic
        cache (empty context) if no context-specific definition exists.
        Updates access tracking when a definition is found.
        
        Args:
            word: The word to look up
            language: Target language code
            context: Sentence or paragraph context
            
        Returns:
            Dictionary with definition data if found, None otherwise:
            {
                'word': str,
                'definition': str,
                'synonym': Optional[str],
                'example': Optional[str],
                'source': 'cache'
            }
        """
        cursor = self.db.conn.cursor()
        
        # Try context-specific cache first
        context_hash = self._hash_context(context)
        cursor.execute("""
            SELECT word, definition, synonym, example_sentence, context_hash
            FROM reading_definition_cache
            WHERE word = ? AND language = ? AND context_hash = ?
        """, (word, language, context_hash))
        
        row = cursor.fetchone()
        
        # If not found, try generic cache (empty context)
        if not row:
            generic_hash = self._hash_context("")
            cursor.execute("""
                SELECT word, definition, synonym, example_sentence, context_hash
                FROM reading_definition_cache
                WHERE word = ? AND language = ? AND context_hash = ?
            """, (word, language, generic_hash))
            row = cursor.fetchone()
        
        if row:
            # Update access tracking
            self._update_access(word, language, row[4])
            
            return {
                'word': row[0],
                'definition': row[1],
                'synonym': row[2],
                'example': row[3],
                'source': 'cache'
            }
        
        return None
    
    def store_definition(
        self,
        word: str,
        language: str,
        context: str,
        definition: str,
        synonym: Optional[str] = None,
        example: Optional[str] = None
    ) -> None:
        """Store a definition in the cache.
        
        If a definition with the same word, language, and context already
        exists, it will be updated (UPSERT behavior).
        
        Args:
            word: The word being defined
            language: Target language code
            context: Sentence or paragraph context
            definition: The definition text
            synonym: Optional simplified synonym
            example: Optional example sentence
        """
        cursor = self.db.conn.cursor()
        context_hash = self._hash_context(context)
        now = datetime.now().isoformat()
        
        # Use INSERT OR REPLACE for upsert behavior
        cursor.execute("""
            INSERT OR REPLACE INTO reading_definition_cache
            (word, language, context_hash, definition, synonym, example_sentence,
             created_at, access_count, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (word, language, context_hash, definition, synonym, example, now, now))
        
        self.db.conn.commit()
    
    def _hash_context(self, context: str) -> str:
        """Generate MD5 hash of context for cache key.
        
        Args:
            context: The context string to hash
            
        Returns:
            32-character hexadecimal MD5 hash
        """
        return hashlib.md5(context.encode('utf-8')).hexdigest()
    
    def _update_access(
        self,
        word: str,
        language: str,
        context_hash: str
    ) -> None:
        """Update access tracking for a cached definition.
        
        Increments access_count and updates last_accessed timestamp.
        
        Args:
            word: The word
            language: Target language code
            context_hash: MD5 hash of the context
        """
        cursor = self.db.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE reading_definition_cache
            SET access_count = access_count + 1,
                last_accessed = ?
            WHERE word = ? AND language = ? AND context_hash = ?
        """, (now, word, language, context_hash))
        
        self.db.conn.commit()
    
    def expire_old_definitions(self, days: int = 30) -> int:
        """Remove definitions not accessed in the specified number of days.
        
        This method helps manage cache size by removing stale definitions
        that haven't been accessed recently. It calculates the cutoff date
        based on the current time and the specified number of days.
        
        Args:
            days: Number of days of inactivity before expiration (default: 30)
            
        Returns:
            Number of definitions removed from the cache
        """
        from datetime import timedelta
        
        cursor = self.db.conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Count definitions to be deleted
        cursor.execute("""
            SELECT COUNT(*)
            FROM reading_definition_cache
            WHERE last_accessed < ?
        """, (cutoff_date,))
        
        count = cursor.fetchone()[0]
        
        # Delete old definitions
        cursor.execute("""
            DELETE FROM reading_definition_cache
            WHERE last_accessed < ?
        """, (cutoff_date,))
        
        self.db.conn.commit()
        
        return count


    def expire_old_definitions(self, days: int = 30) -> int:
        """Remove definitions not accessed in the specified number of days.

        This method helps manage cache size by removing stale definitions
        that haven't been accessed recently. It calculates the cutoff date
        based on the current time and the specified number of days.

        Args:
            days: Number of days of inactivity before expiration (default: 30)

        Returns:
            Number of definitions removed from the cache
        """
        from datetime import timedelta

        cursor = self.db.conn.cursor()

        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Count definitions to be deleted
        cursor.execute("""
            SELECT COUNT(*)
            FROM reading_definition_cache
            WHERE last_accessed < ?
        """, (cutoff_date,))

        count = cursor.fetchone()[0]

        # Delete old definitions
        cursor.execute("""
            DELETE FROM reading_definition_cache
            WHERE last_accessed < ?
        """, (cutoff_date,))

        self.db.conn.commit()

        return count

