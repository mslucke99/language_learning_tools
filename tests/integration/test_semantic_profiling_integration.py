import json
import pytest
import numpy as np
import tempfile
import os
from src.core.database import FlashcardDatabase
from src.services.semantic_visualizer import SemanticVisualizer

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = FlashcardDatabase(path)
    yield database
    try:
        database.close()
    except Exception:
        pass
    try:
        os.unlink(path)
    except Exception:
        pass

def test_get_cluster_profiles_integration(temp_db):
    """Verify that cluster profiles are extracted correctly from flashcards with embeddings."""
    visualizer = SemanticVisualizer(temp_db)
    is_ok, msg = visualizer.check_dependencies()
    if not is_ok:
        pytest.skip(msg)

    # 1. Create a deck and some flashcards with fake embeddings
    deck_id = temp_db.create_deck("Test Deck")
    
    # Cluster A: near [1, 0, 0]
    for i in range(5):
        vec = [1.0 + i*0.01, 0.0, 0.0]
        temp_db.add_flashcard(deck_id, f"word_a_{i}", f"trans_{i}")
        # Need to update with embedding manually since add_flashcard doesn't take it
        cards = temp_db.get_all_flashcards(deck_id)
        card = cards[-1]
        card.embedding_vector = json.dumps(vec)
        # Mock accuracy 100%
        card.history = [
            {"date": "2026-03-01", "success": True},
            {"date": "2026-03-02", "success": True}
        ]
        temp_db.update_flashcard(card)

    # Cluster B: near [0, 1, 0]
    for i in range(5):
        vec = [0.0, 1.0 + i*0.01, 0.0]
        temp_db.add_flashcard(deck_id, f"word_b_{i}", f"trans_{i}")
        cards = temp_db.get_all_flashcards(deck_id)
        card = cards[-1]
        card.embedding_vector = json.dumps(vec)
        # Mock accuracy 20%
        card.history = [
            {"date": "2026-03-01", "success": False},
            {"date": "2026-03-02", "success": False},
            {"date": "2026-03-03", "success": True}
        ]
        temp_db.update_flashcard(card)

    # 2. Extract profiles
    profiles = visualizer.get_cluster_profiles(deck_id)
    
    assert len(profiles) >= 2
    # Verify we have a strong one and a weak one
    strengths = [p.strength for p in profiles]
    assert max(strengths) > min(strengths)
    
    # Check centroids are roughly correct
    # One should be near [1, 0, 0]
    found_a = False
    for p in profiles:
        if p.centroid[0] > 0.9:
            found_a = True
            break
    assert found_a
