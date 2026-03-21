import threading
import time
import queue
import logging
from typing import List, Dict, Optional
from src.core.database import FlashcardDatabase
from src.core.config import config
from src.services.llm_providers.local_embeddings import LocalEmbeddingProvider
from src.features.reader.content_parser import ContentParser

logger = logging.getLogger(__name__)

class EmbeddingWorker:
    """
    Background worker that generates and persists sentence embeddings for library items.
    
    This worker runs in a low-priority thread and processes sessions that don't
    have embeddings yet. It respects the user's 'embedding_speed' preference.
    """
    
    def __init__(self, db: FlashcardDatabase):
        self.db = db
        self.provider = LocalEmbeddingProvider(config.embedding_model_name)
        self.parser = ContentParser()
        self.stop_event = threading.Event()
        self.thread = None
        
    def start(self):
        """Start the background embedding thread."""
        if self.thread and self.thread.is_alive():
            return
            
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name="EmbeddingWorker")
        self.thread.start()
        logger.info("[EmbeddingWorker] Background worker started.")

    def stop(self):
        """Stop the background embedding thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("[EmbeddingWorker] Background worker stopped.")

    def _get_delay(self) -> float:
        """Get the delay between sentences based on config speed."""
        speed = config.embedding_speed.lower()
        if speed == 'fast':
            return 0.1  # 100ms
        elif speed == 'slow':
            return 5.0  # 5 seconds - very low impact
        return 60.0 # Default to very slow if unknown

    def _run(self):
        """Main loop for the background worker."""
        while not self.stop_event.is_set():
            if config.embedding_speed.lower() == 'off':
                time.sleep(10)
                continue
                
            try:
                # 1. Find sessions that need processing
                needs_processing = self.db.get_sessions_needing_embeddings()
                
                if not needs_processing:
                    # Nothing to do, wait a while
                    time.sleep(30)
                    continue
                    
                for session_id in needs_processing:
                    if self.stop_event.is_set():
                        break
                        
                    self._process_session(session_id)
                    
            except Exception as e:
                logger.error(f"[EmbeddingWorker] Error in main loop: {e}")
                time.sleep(10)

    def _process_session(self, session_id: int):
        """Process a single reading session."""
        try:
            # Use a direct query for raw performance in background
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT content, language FROM reading_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return
                
            content, language = row
            
            # Segment into sentences
            parsed = self.parser.parse_content(content)
            sentences = parsed.get('sentences', [])
            
            if not sentences:
                # Mark as "processed" by adding a dummy or just skipping? 
                # For now, let's just avoid re-processing by checking count
                return

            logger.info(f"[EmbeddingWorker] Processing session {session_id} ({len(sentences)} sentences)")
            
            # Process in small matches to allow interruption and respect "Slow" speed
            batch_size = 1
            if config.embedding_speed.lower() == 'fast':
                batch_size = 5
                
            for i in range(0, len(sentences), batch_size):
                if self.stop_event.is_set():
                    return
                if config.embedding_speed.lower() == 'off':
                    return
                    
                batch = sentences[i : i + batch_size]
                
                # Generate embeddings
                embeddings = self.provider.generate_embeddings(batch)
                
                if embeddings:
                    for text, vector in zip(batch, embeddings):
                        # Store in DB
                        import json
                        # Convert vector to something storable (blob or JSON)
                        # The schema expects BLOB (likely pickled or raw floats)
                        import pickle
                        blob = pickle.dumps(vector)
                        self.db.add_sentence_embedding(session_id, text, blob, self.provider.model_name)
                
                # Wait based on speed setting
                time.sleep(self._get_delay())
                
            logger.info(f"[EmbeddingWorker] Finished session {session_id}")
            
        except Exception as e:
            logger.error(f"[EmbeddingWorker] Error processing session {session_id}: {e}")
