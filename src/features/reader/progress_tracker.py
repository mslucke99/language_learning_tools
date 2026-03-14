"""
Reading Progress Tracker for Immersive Reading Mode.

Tracks and saves reading progress automatically to prevent data loss.
Implements auto-save every 30 seconds and force save on close.
"""

import time
from typing import Dict, Optional
from src.core.database import FlashcardDatabase


class ReadingProgressTracker:
    """
    Tracks and saves reading progress automatically.
    
    Implements auto-save strategy:
    - Auto-saves progress every 30 seconds
    - Force save on application close
    - Persists position, completion percentage, and time spent
    
    Requirements:
        - 10.1: Auto-save progress every 30 seconds
        - 3.6: Auto-save reading progress at regular intervals
        - 10.2: Save current position
        - 10.3: Save completion percentage
        - 10.4: Save cumulative time spent
        - 10.5: Save all unsaved progress on close
    """
    
    # Auto-save interval in seconds (Requirement 10.1)
    SAVE_INTERVAL = 30
    
    def __init__(self, session_id: int, db: FlashcardDatabase):
        """
        Initialize the ReadingProgressTracker.
        
        Args:
            session_id: Reading session ID to track progress for
            db: FlashcardDatabase instance for data persistence
        """
        self.session_id = session_id
        self.db = db
        self.last_save = time.time()
        self.pending_changes: Dict[str, any] = {}
    
    def update_position(self, position: int, paragraph: int) -> None:
        """
        Update current reading position.
        
        Stores position changes in pending_changes and triggers
        auto-save if the interval has elapsed.
        
        Args:
            position: Current character offset in content
            paragraph: Current paragraph index
            
        Requirements:
            - 3.5: Update position on navigation
            - 10.2: Save current position
        """
        self.pending_changes['position'] = position
        self.pending_changes['paragraph'] = paragraph
        self._auto_save()
    
    def update_time(self, elapsed_seconds: int) -> None:
        """
        Update time spent reading.
        
        Stores time changes in pending_changes and triggers
        auto-save if the interval has elapsed.
        
        Args:
            elapsed_seconds: Total time spent reading in seconds
            
        Requirements:
            - 10.4: Save cumulative time spent
        """
        self.pending_changes['time'] = elapsed_seconds
        self._auto_save()
    
    def update_completion(self, completion_percentage: float) -> None:
        """
        Update completion percentage.
        
        Stores completion changes in pending_changes and triggers
        auto-save if the interval has elapsed.
        
        Args:
            completion_percentage: Completion percentage (0.0 to 100.0)
            
        Requirements:
            - 10.3: Save completion percentage
        """
        self.pending_changes['completion'] = completion_percentage
        self._auto_save()
    
    def _auto_save(self) -> None:
        """
        Auto-save progress if interval has elapsed.
        
        Checks if SAVE_INTERVAL seconds have passed since the last save.
        If so, triggers a save operation.
        
        Requirements:
            - 10.1: Auto-save every 30 seconds
            - 3.6: Auto-save at regular intervals
        """
        now = time.time()
        if now - self.last_save >= self.SAVE_INTERVAL:
            self._save()
    
    def _save(self) -> None:
        """
        Persist pending changes to database.
        
        Builds a dynamic UPDATE query based on pending changes
        and executes it. Clears pending_changes after successful save.
        
        Requirements:
            - 10.1: Persist progress to database
        """
        if not self.pending_changes:
            return
        
        cursor = self.db.conn.cursor()
        
        # Build update query dynamically
        updates = []
        params = []
        
        if 'position' in self.pending_changes:
            updates.append("current_position = ?")
            params.append(self.pending_changes['position'])
        
        if 'paragraph' in self.pending_changes:
            updates.append("current_paragraph = ?")
            params.append(self.pending_changes['paragraph'])
        
        if 'time' in self.pending_changes:
            updates.append("time_spent_seconds = ?")
            params.append(self.pending_changes['time'])
        
        if 'completion' in self.pending_changes:
            updates.append("completion_percentage = ?")
            params.append(self.pending_changes['completion'])
        
        # Always update last_updated timestamp
        updates.append("last_updated = CURRENT_TIMESTAMP")
        params.append(self.session_id)
        
        query = f"UPDATE reading_progress SET {', '.join(updates)} WHERE session_id = ?"
        cursor.execute(query, params)
        self.db.conn.commit()
        
        # Clear pending changes after successful save
        self.pending_changes = {}
        self.last_save = time.time()
    
    def force_save(self) -> None:
        """
        Force immediate save of all pending changes.
        
        Used when the application is closing or when an
        immediate save is required regardless of the interval.
        
        Requirements:
            - 10.5: Force save on close
        """
        self._save()
    
    def get_pending_changes(self) -> Dict[str, any]:
        """
        Get current pending changes.
        
        Returns:
            Dictionary of pending changes
        """
        return self.pending_changes.copy()
    
    def get_last_save_time(self) -> float:
        """
        Get timestamp of last save.
        
        Returns:
            Unix timestamp of last save
        """
        return self.last_save
