"""
Sync Merger
-----------
Handles row-by-row comparison between local and remote databases.
Detects conflicts and provides resolution strategies.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Literal
from dataclasses import dataclass
from enum import Enum

class ConflictResolution(Enum):
    KEEP_LOCAL = "local"
    KEEP_REMOTE = "remote"
    ALWAYS_LOCAL = "always_local"
    ALWAYS_REMOTE = "always_remote"
    CANCEL = "cancel"

@dataclass
class ConflictInfo:
    table: str
    uuid: str
    local_modified: str
    remote_modified: str
    local_data: Dict
    remote_data: Dict
    description: str  # Human-readable item identifier

# Tables that support sync
SYNCABLE_TABLES = [
    "decks", "flashcards", "imported_content", "word_definitions",
    "sentence_explanations", "writing_sessions", "chat_sessions",
    "grammar_book_entries", "collections"
]

class SyncMerger:
    def __init__(self, local_db_path: str, remote_db_path: str, last_sync_time: Optional[str] = None):
        self.local_conn = sqlite3.connect(local_db_path)
        self.local_conn.row_factory = sqlite3.Row
        self.remote_conn = sqlite3.connect(remote_db_path)
        self.remote_conn.row_factory = sqlite3.Row
        self.last_sync_time = last_sync_time or "1970-01-01T00:00:00"
        
        # Session preferences
        self._always_preference: Optional[ConflictResolution] = None
        
        # Conflict handler callback (set by UI)
        self.on_conflict: Optional[callable] = None
    
    def close(self):
        self.local_conn.close()
        self.remote_conn.close()
    
    def _get_all_rows(self, conn: sqlite3.Connection, table: str) -> Dict[str, Dict]:
        """Get all rows from a table, keyed by UUID."""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE deleted_at IS NULL")
            rows = cursor.fetchall()
            return {row['uuid']: dict(row) for row in rows if row['uuid']}
        except sqlite3.OperationalError:
            return {}  # Table might not exist
    
    def _get_deleted_uuids(self, conn: sqlite3.Connection, table: str) -> set:
        """Get UUIDs of soft-deleted rows."""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT uuid FROM {table} WHERE deleted_at IS NOT NULL")
            return {row[0] for row in cursor.fetchall() if row[0]}
        except sqlite3.OperationalError:
            return set()
    
    def _is_modified_since_sync(self, last_modified: str) -> bool:
        """Check if a row was modified after last sync."""
        if not last_modified:
            return False
        return last_modified > self.last_sync_time
    
    def _resolve_srs_conflict(self, local: Dict, remote: Dict) -> Dict:
        """Special handling for flashcard SRS data: most progress wins."""
        local_reviews = local.get('total_reviews', 0) or 0
        remote_reviews = remote.get('total_reviews', 0) or 0
        
        if local_reviews >= remote_reviews:
            return local
        return remote
    
    def _get_item_description(self, table: str, row: Dict) -> str:
        """Generate human-readable description for conflict dialog."""
        if table == "flashcards":
            return f"Flashcard: {row.get('question', 'Unknown')[:50]}"
        elif table == "decks":
            return f"Deck: {row.get('name', 'Unknown')}"
        elif table == "imported_content":
            return f"Import: {row.get('content', 'Unknown')[:50]}"
        elif table == "word_definitions":
            return f"Word: {row.get('word', 'Unknown')}"
        elif table == "sentence_explanations":
            return f"Sentence: {row.get('sentence', 'Unknown')[:50]}"
        elif table == "writing_sessions":
            return f"Essay: {row.get('topic', 'Unknown')[:50]}"
        elif table == "chat_sessions":
            return f"Chat: {row.get('cur_topic', 'Unknown')[:50]}"
        elif table == "grammar_book_entries":
            return f"Grammar: {row.get('title', 'Unknown')}"
        return f"{table}: {row.get('uuid', 'Unknown')[:8]}"
    
    def merge_table(self, table: str) -> Tuple[int, int, int]:
        """
        Merge a single table. Returns (added, updated, conflicts).
        """
        local_rows = self._get_all_rows(self.local_conn, table)
        remote_rows = self._get_all_rows(self.remote_conn, table)
        local_deleted = self._get_deleted_uuids(self.local_conn, table)
        remote_deleted = self._get_deleted_uuids(self.remote_conn, table)
        
        added = 0
        updated = 0
        conflicts = 0
        
        local_cursor = self.local_conn.cursor()
        
        # Process remote rows
        for uuid, remote_row in remote_rows.items():
            # Skip if deleted locally
            if uuid in local_deleted:
                continue
            
            local_row = local_rows.get(uuid)
            
            if local_row is None:
                # New item from remote - add it
                self._insert_row(local_cursor, table, remote_row)
                added += 1
            else:
                # Both exist - check for conflict
                local_modified = self._is_modified_since_sync(local_row.get('last_modified'))
                remote_modified = self._is_modified_since_sync(remote_row.get('last_modified'))
                
                if local_modified and remote_modified:
                    # CONFLICT!
                    conflicts += 1
                    
                    # Special case: Flashcard SRS - auto-resolve
                    if table == "flashcards":
                        winner = self._resolve_srs_conflict(local_row, remote_row)
                        if winner == remote_row:
                            self._update_row(local_cursor, table, remote_row)
                            updated += 1
                        continue
                    
                    # Check session preference
                    if self._always_preference == ConflictResolution.ALWAYS_LOCAL:
                        continue  # Keep local, do nothing
                    elif self._always_preference == ConflictResolution.ALWAYS_REMOTE:
                        self._update_row(local_cursor, table, remote_row)
                        updated += 1
                        continue
                    
                    # Ask user
                    if self.on_conflict:
                        conflict = ConflictInfo(
                            table=table,
                            uuid=uuid,
                            local_modified=local_row.get('last_modified', ''),
                            remote_modified=remote_row.get('last_modified', ''),
                            local_data=local_row,
                            remote_data=remote_row,
                            description=self._get_item_description(table, local_row)
                        )
                        resolution = self.on_conflict(conflict)
                        
                        if resolution == ConflictResolution.CANCEL:
                            raise Exception("Sync cancelled by user")
                        elif resolution in (ConflictResolution.KEEP_REMOTE, ConflictResolution.ALWAYS_REMOTE):
                            self._update_row(local_cursor, table, remote_row)
                            updated += 1
                            if resolution == ConflictResolution.ALWAYS_REMOTE:
                                self._always_preference = ConflictResolution.ALWAYS_REMOTE
                        elif resolution == ConflictResolution.ALWAYS_LOCAL:
                            self._always_preference = ConflictResolution.ALWAYS_LOCAL
                        # KEEP_LOCAL: do nothing
                
                elif remote_modified and not local_modified:
                    # Only remote changed - take remote
                    self._update_row(local_cursor, table, remote_row)
                    updated += 1
                # If only local changed or neither, keep local (do nothing)
        
        # Handle items deleted on remote
        for uuid in remote_deleted:
            if uuid in local_rows:
                local_row = local_rows[uuid]
                local_modified = self._is_modified_since_sync(local_row.get('last_modified'))
                
                if local_modified:
                    # Conflict: Remote deleted but local edited
                    # For now, keep local (user's edits win over deletions)
                    pass
                else:
                    # Safe to delete locally
                    self._soft_delete_row(local_cursor, table, uuid)
        
        self.local_conn.commit()
        return added, updated, conflicts
    
    def _insert_row(self, cursor, table: str, row: Dict):
        """Insert a new row."""
        columns = [k for k in row.keys() if k != 'id']
        placeholders = ', '.join(['?' for _ in columns])
        col_names = ', '.join(columns)
        values = [row[c] for c in columns]
        cursor.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values)
    
    def _update_row(self, cursor, table: str, row: Dict):
        """Update existing row by UUID."""
        columns = [k for k in row.keys() if k not in ('id', 'uuid')]
        set_clause = ', '.join([f"{c} = ?" for c in columns])
        values = [row[c] for c in columns] + [row['uuid']]
        cursor.execute(f"UPDATE {table} SET {set_clause} WHERE uuid = ?", values)
    
    def _soft_delete_row(self, cursor, table: str, uuid: str):
        """Mark row as deleted."""
        now = datetime.now().isoformat()
        cursor.execute(f"UPDATE {table} SET deleted_at = ? WHERE uuid = ?", (now, uuid))
    
    def merge_all(self) -> Dict[str, Tuple[int, int, int]]:
        """Merge all syncable tables. Returns stats per table."""
        results = {}
        for table in SYNCABLE_TABLES:
            try:
                results[table] = self.merge_table(table)
            except Exception as e:
                print(f"Error merging {table}: {e}")
                results[table] = (0, 0, 0)
        return results
