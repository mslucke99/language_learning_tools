from datetime import datetime, timedelta
from .flashcard import Flashcard

def get_due_flashcards(flashcards: list[Flashcard]) -> list[Flashcard]:
    """Filter flashcards that are due for review."""
    now = datetime.now()
    return [fc for fc in flashcards if fc.is_due(now)]

def get_next_review_date(flashcard: Flashcard) -> datetime:
    """Calculate the next review date for a flashcard."""
    if not flashcard.last_reviewed:
        return datetime.now()
    return flashcard.last_reviewed + timedelta(days=flashcard.interval)

def get_review_statistics(flashcards: list[Flashcard]) -> dict:
    """Get review statistics for a list of flashcards."""
    if not flashcards:
        return {
            "total": 0,
            "reviewed": 0,
            "new": 0,
            "avg_accuracy": 0.0,
            "avg_easiness": 0.0,
            "avg_interval": 0.0
        }
    
    reviewed = sum(1 for fc in flashcards if fc.total_reviews > 0)
    new = len(flashcards) - reviewed
    total_accuracy = sum(fc.get_accuracy() for fc in flashcards if fc.total_reviews > 0)
    avg_accuracy = total_accuracy / reviewed if reviewed > 0 else 0.0
    avg_easiness = sum(fc.easiness for fc in flashcards) / len(flashcards)
    avg_interval = sum(fc.interval for fc in flashcards) / len(flashcards)
    
    return {
        "total": len(flashcards),
        "reviewed": reviewed,
        "new": new,
        "avg_accuracy": avg_accuracy,
        "avg_easiness": avg_easiness,
        "avg_interval": avg_interval
    }