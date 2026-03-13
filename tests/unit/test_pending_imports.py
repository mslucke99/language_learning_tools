import os
import json
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from src.core.pending_imports import PendingImportsProcessor
from src.core.database import FlashcardDatabase

class TestPendingImports:
    @pytest.fixture
    def db(self):
        # Create a temporary database file
        handle, path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        db = FlashcardDatabase(path)
        yield db
        db.close()
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    def test_processes_valid_queue_file(self, db, temp_dir):
        # Create a dummy queue file
        test_data = [
            {
                "content_type": "word",
                "content": "test_word",
                "url": "http://example.com",
                "title": "Example",
                "context": "This is a test word context."
            },
            {
                "content_type": "sentence",
                "content": "This is a test sentence.",
                "url": "http://example.com/sentence",
                "title": "Example Sentence"
            }
        ]
        
        file_path = os.path.join(temp_dir, PendingImportsProcessor.FILENAME)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
            
        processor = PendingImportsProcessor(db)
        # Override search paths for testing
        processor.search_paths = [temp_dir]
        
        results = processor.process()
        
        # Verify results
        assert results["processed"] == 2
        assert len(results["files"]) == 1
        
        # Verify database
        cursor = db.conn.cursor()
        cursor.execute("SELECT content FROM imported_content")
        items = [r[0] for r in cursor.fetchall()]
        assert "test_word" in items
        assert "This is a test sentence." in items
        
        # Verify file is archived (original is gone)
        assert not os.path.exists(file_path)
        # Check for archive file
        archived_files = [f for f in os.listdir(temp_dir) if "processed" in f]
        assert len(archived_files) == 1

    def test_handles_missing_fields(self, db, temp_dir):
        test_data = [
            {
                "content_type": "word",
                "content": "valid_item",
                "url": "http://valid.com"
            },
            {
                "content_type": "word",
                # missing content
                "url": "http://invalid.com"
            }
        ]
        
        file_path = os.path.join(temp_dir, PendingImportsProcessor.FILENAME)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
            
        processor = PendingImportsProcessor(db)
        processor.search_paths = [temp_dir]
        
        results = processor.process()
        
        assert results["processed"] == 1
        assert results["failed"] == 1

    def test_malformed_json(self, db, temp_dir):
        file_path = os.path.join(temp_dir, PendingImportsProcessor.FILENAME)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("this is not json")
            
        processor = PendingImportsProcessor(db)
        processor.search_paths = [temp_dir]
        
        results = processor.process()
        
        assert results["processed"] == 0
        assert len(results["files"]) == 1 # still found and archived even if malformed (to clear it out)
        assert not os.path.exists(file_path)
