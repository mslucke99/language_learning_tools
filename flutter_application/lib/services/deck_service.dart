import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class DeckService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Create a new deck
  Future<int> createDeck({
    required String name,
    String? description,
    String? language,
    int? collectionId,
  }) async {
    final now = DateTime.now().toIso8601String();
    
    return await _db.insertItem('decks', {
      'name': name,
      'description': description,
      'language': language,
      'collection_id': collectionId,
      'created_at': now,
    });
  }

  /// Get all decks
  Future<List<Deck>> getAllDecks({String? language}) async {
    final db = await _db.database;
    
    String query = '''
      SELECT * FROM decks 
      WHERE deleted_at IS NULL
    ''';
    
    List<dynamic> args = [];
    
    if (language != null) {
      query += ' AND (language = ? OR language IS NULL)';
      args.add(language);
    }
    
    query += ' ORDER BY name ASC';
    
    final result = await db.rawQuery(query, args);
    return result.map((json) => Deck.fromJson(json)).toList();
  }

  /// Get a single deck
  Future<Deck?> getDeck(int deckId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'decks',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [deckId],
    );
    
    if (result.isEmpty) {
      return null;
    }
    
    return Deck.fromJson(result.first);
  }

  /// Update a deck
  Future<void> updateDeck(
    int deckId, {
    String? name,
    String? description,
    String? language,
    int? collectionId,
  }) async {
    final updates = <String, dynamic>{};
    
    if (name != null) updates['name'] = name;
    if (description != null) updates['description'] = description;
    if (language != null) updates['language'] = language;
    if (collectionId != null) updates['collection_id'] = collectionId;
    
    if (updates.isNotEmpty) {
      await _db.updateItem('decks', deckId, updates);
    }
  }

  /// Delete a deck (soft delete)
  Future<void> deleteDeck(int deckId) async {
    await _db.softDelete('decks', deckId);
  }

  /// Get deck statistics
  Future<Map<String, dynamic>> getDeckStatistics(int deckId) async {
    final db = await _db.database;
    
    // Count total cards
    final totalResult = await db.rawQuery('''
      SELECT COUNT(*) as count
      FROM flashcards
      WHERE deck_id = ? AND deleted_at IS NULL
    ''', [deckId]);
    
    final total = totalResult.first['count'] as int;
    
    // Count due cards
    final dueResult = await db.rawQuery('''
      SELECT COUNT(*) as count
      FROM flashcards
      WHERE deck_id = ? 
        AND deleted_at IS NULL
        AND (last_reviewed IS NULL 
          OR (julianday('now') - julianday(last_reviewed)) >= interval)
    ''', [deckId]);
    
    final due = dueResult.first['count'] as int;
    
    // Get review statistics
    final statsResult = await db.rawQuery('''
      SELECT 
        SUM(correct_reviews) as correct,
        SUM(total_reviews) as total_reviews
      FROM flashcards
      WHERE deck_id = ? AND deleted_at IS NULL
    ''', [deckId]);
    
    final correct = statsResult.first['correct'] as int? ?? 0;
    final totalReviews = statsResult.first['total_reviews'] as int? ?? 0;
    
    final accuracy = totalReviews > 0 ? (correct / totalReviews * 100) : 0.0;
    
    return {
      'total_cards': total,
      'due_cards': due,
      'total_reviews': totalReviews,
      'correct_reviews': correct,
      'overall_accuracy': accuracy,
    };
  }

  /// Add a flashcard to a deck
  Future<int> addFlashcard({
    required int deckId,
    required String question,
    required String answer,
  }) async {
    final now = DateTime.now().toIso8601String();
    
    return await _db.insertItem('flashcards', {
      'deck_id': deckId,
      'question': question,
      'answer': answer,
      'easiness': 2.5,
      'interval': 1,
      'repetitions': 0,
      'total_reviews': 0,
      'correct_reviews': 0,
      'created_at': now,
    });
  }

  /// Get all flashcards in a deck
  Future<List<Flashcard>> getFlashcards(int deckId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'flashcards',
      where: 'deck_id = ? AND deleted_at IS NULL',
      whereArgs: [deckId],
      orderBy: 'id ASC',
    );
    
    return result.map((json) => Flashcard.fromJson(json)).toList();
  }

  /// Get a single flashcard
  Future<Flashcard?> getFlashcard(int flashcardId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'flashcards',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [flashcardId],
    );
    
    if (result.isEmpty) {
      return null;
    }
    
    return Flashcard.fromJson(result.first);
  }

  /// Update a flashcard
  Future<void> updateFlashcard(
    int flashcardId, {
    String? question,
    String? answer,
    String? userNotes,
  }) async {
    final updates = <String, dynamic>{};
    
    if (question != null) updates['question'] = question;
    if (answer != null) updates['answer'] = answer;
    if (userNotes != null) updates['user_notes'] = userNotes;
    
    if (updates.isNotEmpty) {
      await _db.updateItem('flashcards', flashcardId, updates);
    }
  }

  /// Delete a flashcard (soft delete)
  Future<void> deleteFlashcard(int flashcardId) async {
    await _db.softDelete('flashcards', flashcardId);
  }

  /// Bulk import flashcards from text
  Future<int> bulkImportFlashcards({
    required int deckId,
    required String text,
    String separator = '\t',
  }) async {
    final lines = text.split('\n').where((line) => line.trim().isNotEmpty);
    int count = 0;
    
    for (final line in lines) {
      final parts = line.split(separator);
      if (parts.length >= 2) {
        final question = parts[0].trim();
        final answer = parts[1].trim();
        
        if (question.isNotEmpty && answer.isNotEmpty) {
          await addFlashcard(
            deckId: deckId,
            question: question,
            answer: answer,
          );
          count++;
        }
      }
    }
    
    return count;
  }

  /// Search flashcards by question
  Future<List<Map<String, dynamic>>> findFlashcardByQuestion(
    String question,
  ) async {
    final db = await _db.database;
    
    final result = await db.rawQuery('''
      SELECT f.id, f.question, f.answer, d.name as deck_name
      FROM flashcards f
      JOIN decks d ON f.deck_id = d.id
      WHERE LOWER(f.question) = LOWER(?) AND f.deleted_at IS NULL
    ''', [question.trim()]);
    
    return result.map((row) => {
      'id': row['id'],
      'question': row['question'],
      'answer': row['answer'],
      'deck_name': row['deck_name'],
    }).toList();
  }
}
