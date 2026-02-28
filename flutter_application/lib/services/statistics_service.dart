import 'package:proficiency_suites/services/database_helper.dart';

class StatisticsService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Get overall statistics
  Future<Map<String, dynamic>> getOverallStats({
    String? language,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final db = await _db.database;
    
    // Build date filter
    String dateFilter = '';
    List<dynamic> dateArgs = [];
    
    if (startDate != null) {
      dateFilter += ' AND review_date >= ?';
      dateArgs.add(startDate.toIso8601String());
    }
    if (endDate != null) {
      dateFilter += ' AND review_date <= ?';
      dateArgs.add(endDate.toIso8601String());
    }

    // Total reviews
    final reviewResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM review_logs WHERE deleted_at IS NULL$dateFilter',
      dateArgs.isNotEmpty ? dateArgs : null,
    );
    final totalReviews = reviewResult.first['count'] as int;

    // Correct reviews (grade >= 3)
    final correctResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM review_logs WHERE deleted_at IS NULL AND grade >= 3$dateFilter',
      dateArgs.isNotEmpty ? dateArgs : null,
    );
    final correctReviews = correctResult.first['count'] as int;

    // Calculate accuracy
    final accuracy = totalReviews > 0 ? (correctReviews / totalReviews * 100) : 0.0;

    // Study streak
    final streak = await calculateStreak(language: language);

    // Cards due today
    final dueCards = await getDueCardsCount(language: language);

    return {
      'total_reviews': totalReviews,
      'correct_reviews': correctReviews,
      'accuracy': accuracy,
      'streak': streak,
      'due_cards': dueCards,
    };
  }

  /// Get deck-specific statistics
  Future<Map<String, dynamic>> getDeckStats(int deckId) async {
    final db = await _db.database;

    // Total cards in deck
    final cardResult = await db.rawQuery(
      'SELECT COUNT(*) as count FROM flashcards WHERE deck_id = ? AND deleted_at IS NULL',
      [deckId],
    );
    final totalCards = cardResult.first['count'] as int;

    // Cards reviewed
    final reviewedResult = await db.rawQuery(
      'SELECT COUNT(DISTINCT flashcard_id) as count FROM review_logs '
      'WHERE flashcard_id IN (SELECT id FROM flashcards WHERE deck_id = ? AND deleted_at IS NULL)',
      [deckId],
    );
    final reviewedCards = reviewedResult.first['count'] as int;

    // Average easiness
    final easinessResult = await db.rawQuery(
      'SELECT AVG(easiness) as avg FROM flashcards WHERE deck_id = ? AND deleted_at IS NULL AND easiness IS NOT NULL',
      [deckId],
    );
    final avgEasiness = easinessResult.first['avg'] as double? ?? 2.5;

    // Retention rate
    final retentionRate = await getRetentionRate(deckId);

    return {
      'total_cards': totalCards,
      'reviewed_cards': reviewedCards,
      'avg_easiness': avgEasiness,
      'retention_rate': retentionRate,
    };
  }

  /// Get review history for charts
  Future<List<Map<String, dynamic>>> getReviewHistory({
    String? language,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final db = await _db.database;
    
    String dateFilter = '';
    List<dynamic> dateArgs = [];
    
    if (startDate != null) {
      dateFilter += ' AND review_date >= ?';
      dateArgs.add(startDate.toIso8601String());
    }
    if (endDate != null) {
      dateFilter += ' AND review_date <= ?';
      dateArgs.add(endDate.toIso8601String());
    }

    final result = await db.rawQuery('''
      SELECT 
        DATE(review_date) as date,
        COUNT(*) as count,
        SUM(CASE WHEN grade >= 3 THEN 1 ELSE 0 END) as correct
      FROM review_logs
      WHERE deleted_at IS NULL$dateFilter
      GROUP BY DATE(review_date)
      ORDER BY date ASC
    ''', dateArgs.isNotEmpty ? dateArgs : null);

    return result;
  }

  /// Get quiz performance over time
  Future<List<Map<String, dynamic>>> getQuizPerformance({
    String? language,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final db = await _db.database;
    
    String dateFilter = '';
    List<dynamic> dateArgs = [];
    
    if (startDate != null) {
      dateFilter += ' AND created_at >= ?';
      dateArgs.add(startDate.toIso8601String());
    }
    if (endDate != null) {
      dateFilter += ' AND created_at <= ?';
      dateArgs.add(endDate.toIso8601String());
    }

    final result = await db.rawQuery('''
      SELECT 
        DATE(created_at) as date,
        COUNT(*) as quiz_count,
        AVG(CAST(score AS REAL) / CAST(total_questions AS REAL) * 100) as avg_score
      FROM quiz_sessions
      WHERE deleted_at IS NULL AND score IS NOT NULL$dateFilter
      GROUP BY DATE(created_at)
      ORDER BY date ASC
    ''', dateArgs.isNotEmpty ? dateArgs : null);

    return result;
  }

  /// Get writing session grades
  Future<List<Map<String, dynamic>>> getWritingGrades({
    String? language,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final db = await _db.database;
    
    String whereClause = 'deleted_at IS NULL AND grade IS NOT NULL';
    List<dynamic> whereArgs = [];
    
    if (language != null) {
      whereClause += ' AND study_language = ?';
      whereArgs.add(language);
    }
    
    if (startDate != null) {
      whereClause += ' AND created_at >= ?';
      whereArgs.add(startDate.toIso8601String());
    }
    if (endDate != null) {
      whereClause += ' AND created_at <= ?';
      whereArgs.add(endDate.toIso8601String());
    }

    final result = await db.query(
      'writing_sessions',
      columns: ['created_at', 'grade', 'topic'],
      where: whereClause,
      whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
      orderBy: 'created_at ASC',
    );

    return result;
  }

  /// Calculate study streak
  Future<int> calculateStreak({String? language}) async {
    final db = await _db.database;
    
    // Get all review dates in descending order
    final result = await db.rawQuery('''
      SELECT DISTINCT DATE(review_date) as date
      FROM review_logs
      WHERE deleted_at IS NULL
      ORDER BY date DESC
    ''');

    if (result.isEmpty) return 0;

    int streak = 0;
    DateTime? lastDate;
    final today = DateTime.now();
    final todayDate = DateTime(today.year, today.month, today.day);

    for (var row in result) {
      final dateStr = row['date'] as String;
      final date = DateTime.parse(dateStr);
      
      if (lastDate == null) {
        // First date - check if it's today or yesterday
        final diff = todayDate.difference(date).inDays;
        if (diff > 1) break; // Streak broken
        streak = 1;
        lastDate = date;
      } else {
        // Check if consecutive
        final diff = lastDate.difference(date).inDays;
        if (diff == 1) {
          streak++;
          lastDate = date;
        } else {
          break; // Streak broken
        }
      }
    }

    return streak;
  }

  /// Get due cards count
  Future<int> getDueCardsCount({String? language}) async {
    final db = await _db.database;
    
    String languageFilter = '';
    List<dynamic>? languageArgs;
    
    if (language != null) {
      languageFilter = ' AND deck_id IN (SELECT id FROM decks WHERE language = ?)';
      languageArgs = [language];
    }

    final result = await db.rawQuery('''
      SELECT COUNT(*) as count FROM flashcards
      WHERE deleted_at IS NULL
        AND (last_reviewed IS NULL 
          OR (julianday('now') - julianday(last_reviewed)) >= interval)
        $languageFilter
    ''', languageArgs);

    return result.first['count'] as int;
  }

  /// Calculate retention rate for a deck
  Future<double> getRetentionRate(int deckId) async {
    final db = await _db.database;
    
    // Get cards reviewed in last 30 days
    final result = await db.rawQuery('''
      SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN grade >= 3 THEN 1 ELSE 0 END) as remembered
      FROM review_logs
      WHERE flashcard_id IN (SELECT id FROM flashcards WHERE deck_id = ? AND deleted_at IS NULL)
        AND deleted_at IS NULL
        AND review_date >= datetime('now', '-30 days')
    ''', [deckId]);

    final total = result.first['total'] as int;
    final remembered = result.first['remembered'] as int;

    return total > 0 ? (remembered / total * 100) : 0.0;
  }

  /// Get statistics by language
  Future<Map<String, Map<String, dynamic>>> getStatsByLanguage() async {
    final db = await _db.database;
    
    // Get all languages
    final langResult = await db.rawQuery('''
      SELECT DISTINCT language FROM decks WHERE deleted_at IS NULL AND language IS NOT NULL
    ''');

    Map<String, Map<String, dynamic>> stats = {};

    for (var row in langResult) {
      final language = row['language'] as String;
      stats[language] = await getOverallStats(language: language);
    }

    return stats;
  }
}
