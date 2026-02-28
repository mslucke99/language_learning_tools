import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class FlashcardReviewService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Start a review session for a deck
  Future<List<Flashcard>> startReviewSession(int deckId) async {
    return await getDueCards(deckId);
  }

  /// Get flashcards due for review
  Future<List<Flashcard>> getDueCards(int deckId) async {
    final db = await _db.database;
    
    // Query for due cards (no last_reviewed OR days since review >= interval)
    final result = await db.rawQuery('''
      SELECT * FROM flashcards
      WHERE deck_id = ? 
        AND deleted_at IS NULL
        AND (last_reviewed IS NULL 
          OR (julianday('now') - julianday(last_reviewed)) >= interval)
      ORDER BY last_reviewed ASC, id ASC
    ''', [deckId]);

    return result.map((json) => Flashcard.fromJson(json)).toList();
  }

  /// Get count of flashcards due for review
  Future<int> getDueCardsCount(int deckId) async {
    final db = await _db.database;
    
    final result = await db.rawQuery('''
      SELECT COUNT(*) as count FROM flashcards
      WHERE deck_id = ? 
        AND deleted_at IS NULL
        AND (last_reviewed IS NULL 
          OR (julianday('now') - julianday(last_reviewed)) >= interval)
    ''', [deckId]);

    return result.first['count'] as int;
  }

  /// Rate a flashcard and update using SuperMemo SM-2 algorithm
  Future<void> rateCard(Flashcard card, int quality, int timeTaken) async {
    if (quality < 0 || quality > 5) {
      throw ArgumentError('Quality must be between 0 and 5');
    }

    final now = DateTime.now().toIso8601String();
    
    // Update statistics
    int totalReviews = (card.totalReviews ?? 0) + 1;
    int correctReviews = card.correctReviews ?? 0;
    
    if (quality >= 3) {
      correctReviews++;
    }

    // SuperMemo SM-2 algorithm
    int repetitions = card.repetitions ?? 0;
    int interval = card.interval ?? 1;
    double easiness = card.easiness ?? 2.5;

    if (quality < 3) {
      // Failed - reset
      repetitions = 0;
      interval = 1;
    } else {
      // Passed - increase interval
      if (repetitions == 0) {
        interval = 1;
      } else if (repetitions == 1) {
        interval = 3;
      } else {
        interval = (interval * easiness).round();
      }
      repetitions++;
    }

    // Update easiness factor (SM-2 formula)
    easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    
    // Minimum easiness is 1.3
    if (easiness < 1.3) {
      easiness = 1.3;
    }

    // Update the flashcard
    final updatedCard = {
      'last_reviewed': now,
      'easiness': easiness,
      'interval': interval,
      'repetitions': repetitions,
      'total_reviews': totalReviews,
      'correct_reviews': correctReviews,
      'last_modified': now,
    };

    await _db.updateItem('flashcards', card.id!, updatedCard);

    // Log the review
    await logReview(card.id!, quality, timeTaken);
  }

  /// Log a review event for statistics
  Future<void> logReview(int flashcardId, int grade, int timeTaken) async {
    final now = DateTime.now().toIso8601String();
    
    await _db.insertItem('review_logs', {
      'flashcard_id': flashcardId,
      'review_desc': 'flashcard',
      'grade': grade,
      'time_taken': timeTaken,
      'review_date': now,
    });
  }

  /// Calculate accuracy for a flashcard
  double calculateAccuracy(Flashcard card) {
    if (card.totalReviews == null || card.totalReviews == 0) {
      return 0.0;
    }
    return ((card.correctReviews ?? 0) / card.totalReviews!) * 100;
  }

  /// Check if a flashcard is due for review
  bool isDue(Flashcard card) {
    if (card.lastReviewed == null) {
      return true;
    }

    final lastReviewed = DateTime.parse(card.lastReviewed!);
    final daysSinceReview = DateTime.now().difference(lastReviewed).inDays;
    
    return daysSinceReview >= (card.interval ?? 1);
  }

  /// Get review statistics for a session
  Map<String, dynamic> getSessionStats(List<Flashcard> reviewedCards) {
    int total = reviewedCards.length;
    int correct = reviewedCards.where((card) => 
      (card.correctReviews ?? 0) > 0
    ).length;

    return {
      'total_reviewed': total,
      'correct': correct,
      'accuracy': total > 0 ? (correct / total * 100) : 0.0,
    };
  }
}
