import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import firebase_admin
from firebase_admin import firestore
from src.services.firebase_config import get_firestore_client
from src.services.sync_merger import SyncMerger, SYNCABLE_TABLES

logger = logging.getLogger("FirestoreSync")

class FirestoreSyncManager:
    """
    Manages synchronization between local SQLite and Firestore.
    """
    def __init__(self, local_db_path: str, user_id: Optional[str] = None):
        self.local_db_path = local_db_path
        self.db = get_firestore_client()
        self.user_id = user_id
        self.last_sync_time = "1970-01-01T00:00:00" # TODO: Load from config
    
    def set_user_id(self, user_id: str):
        self.user_id = user_id

    def _get_collection_ref(self, collection_name: str):
        if not self.user_id:
            raise ValueError("No user ID set for sync.")
        return self.db.collection('users').document(self.user_id).collection(collection_name)

    def is_authenticated(self) -> bool:
        return self.db is not None

    def sync(self) -> Dict[str, Dict]:
        if not self.db:
            return {"error": "Not authenticated"}

        stats = {
            "downloaded": 0,
            "uploaded": 0,
            "conflicts": 0
        }
        
        # We need to persist sync time, for now just use memory or a file
        # In a real app, this should be stored in a preferences file.
        # self.last_sync_time = load_last_sync_time()

        merger = SyncMerger(self.local_db_path, remote_db_path=None, last_sync_time=self.last_sync_time)
        new_sync_time = datetime.now().isoformat()

        try:
            for table in SYNCABLE_TABLES:
                # 1. Pull from Firestore (Remote -> Local)
                remote_updates = self._fetch_remote_changes(table, self.last_sync_time)
                if remote_updates:
                    added, updated, conflicts, _ = merger.merge_from_data(table, remote_updates)
                    stats["downloaded"] += (added + updated)
                    stats["conflicts"] += conflicts

                # 2. Push to Firestore (Local -> Remote)
                local_updates = merger.get_modified_rows_since(table, self.last_sync_time)
                if local_updates:
                    self._push_local_changes(table, local_updates)
                    stats["uploaded"] += len(local_updates)

            self.last_sync_time = new_sync_time
            # save_last_sync_time(new_sync_time)
            
            return stats

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {"error": str(e)}
        finally:
            merger.close()

    def _fetch_remote_changes(self, collection_name: str, since: str) -> List[Dict]:
        """Query Firestore for documents modified after 'since'."""
        try:
            docs_ref = self._get_collection_ref(collection_name)
            query = docs_ref.where("last_modified", ">", since)
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except ValueError:
            logger.warning(f"Skipping fetch for {collection_name}: User not logged in.")
            return []

    def _push_local_changes(self, collection_name: str, rows: List[Dict]):
        """Upload local changes to Firestore using batch writes."""
        batch = self.db.batch()
        count = 0
        MAX_BATCH_SIZE = 500

        for row in rows:
            doc_ref = self._get_collection_ref(collection_name).document(row['uuid'])
            # Ensure 'id' (integer PK) is not uploaded if not needed, or keep it.
            # Firestore doesn't enforce schema, so extra fields are fine.
            # Convert row to dict if it's not already
            row_data = dict(row)
            batch.set(doc_ref, row_data, merge=True)
            count += 1

            if count >= MAX_BATCH_SIZE:
                batch.commit()
                batch = self.db.batch()
                count = 0
        
        if count > 0:
            batch.commit()
