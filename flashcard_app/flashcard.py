from datetime import datetime

class Flashcard:
    def __init__(self, question: str, answer: str, card_id: int = None):
        self.id = card_id
        self.question = question
        self.answer = answer
        self.last_reviewed = None  # datetime
        self.easiness = 2.5         # SM-2 easiness factor
        self.interval = 1           # Days until next review
        self.repetitions = 0        # Number of times reviewed correctly in a row
        self.total_reviews = 0      # Total number of reviews
        self.correct_reviews = 0    # Number of correct reviews

    def mark_reviewed(self, quality: int):
        """
        Update flashcard stats using SM-2 algorithm.
        quality: 0-5 rating (5=perfect, 4=correct, 3=correct with effort,
                 2=incorrect but remembered, 1=very poor memory, 0=complete blank)
        """
        now = datetime.now()
        self.total_reviews += 1
        
        if quality >= 3:
            self.correct_reviews += 1
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 3
            else:
                self.interval = int(self.interval * self.easiness)
            self.repetitions += 1
        else:
            self.repetitions = 0
            self.interval = 1
        
        # Update easiness factor (SM-2)
        self.easiness = max(1.3, self.easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        self.last_reviewed = now

    def is_due(self, now: datetime) -> bool:
        """Check if the flashcard is due for review."""
        if not self.last_reviewed:
            return True
        days_since_review = (now - self.last_reviewed).total_seconds() / 86400
        return days_since_review >= self.interval
    
    def get_accuracy(self) -> float:
        """Get the accuracy percentage."""
        if self.total_reviews == 0:
            return 0.0
        return (self.correct_reviews / self.total_reviews) * 100