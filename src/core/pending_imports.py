import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PendingImportsProcessor:
    """
    Processes 'proficiency_pending_imports.json' files exported by the browser extension.
    Checks the user's Downloads folder and the app data directory on startup.
    """
    
    FILENAME = "proficiency_pending_imports.json"
    
    def __init__(self, db):
        self.db = db
        # Potential search locations
        self.search_paths = [
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data")
        ]

    def process(self):
        """
        Finds, reads, imports, and archives any pending import files.
        Returns a dict with summary of actions.
        """
        total_processed = 0
        total_failed = 0
        files_found = []

        for base_path in self.search_paths:
            file_path = os.path.join(base_path, self.FILENAME)
            if os.path.exists(file_path):
                logger.info(f"Found pending imports file: {file_path}")
                processed, failed = self._process_file(file_path)
                total_processed += processed
                total_failed += failed
                files_found.append(file_path)
                
                # Archive the file
                self._archive_file(file_path)

        return {
            "processed": total_processed,
            "failed": total_failed,
            "files": files_found
        }

    def _process_file(self, file_path):
        processed = 0
        failed = 0
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            
            if not isinstance(items, list):
                logger.error(f"Invalid format in {file_path}: expected list")
                return 0, 0

            for item in items:
                try:
                    content_type = item.get("content_type", "word")
                    content = item.get("content", "").strip()
                    url = item.get("url", "").strip()
                    title = item.get("title", "").strip()
                    context = item.get("context", "").strip()
                    language = item.get("language", "").strip()
                    tags = item.get("tags", "").strip()

                    if not content or not url:
                        failed += 1
                        continue

                    # Call the database to add the content
                    content_id = self.db.add_imported_content(
                        content_type=content_type,
                        content=content,
                        url=url,
                        title=title,
                        context=context,
                        language=language,
                        tags=tags
                    )
                    
                    if content_id:
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Error importing item: {e}")
                    failed += 1
                    
        except Exception as e:
            logger.error(f"Failed to read/parse {file_path}: {e}")
            
        return processed, failed

    def _archive_file(self, file_path):
        """Rename the file to avoid re-processing it."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"proficiency_pending_imports.processed_{timestamp}.json"
            archive_path = os.path.join(os.path.dirname(file_path), archive_name)
            
            os.rename(file_path, archive_path)
            logger.info(f"Archived pending imports file to: {archive_path}")
        except Exception as e:
            logger.error(f"Failed to archive file {file_path}: {e}")
