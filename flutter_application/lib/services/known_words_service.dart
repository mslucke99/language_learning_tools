import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class KnownWordsService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Add a single word to known words
  Future<int> addWord(String lemma, String language, {String? source}) async {
    final now = DateTime.now().toIso8601String();
    
    try {
      return await _db.insertItem('known_words', {
        'lemma': lemma.toLowerCase(),
        'language': language,
        'source': source ?? 'user',
        'added_at': now,
      });
    } catch (e) {
      // Word might already exist (UNIQUE constraint)
      return -1;
    }
  }

  /// Add multiple words in bulk
  Future<int> addWordsBulk(
    List<String> lemmas,
    String language, {
    String? source,
  }) async {
    int added = 0;
    for (var lemma in lemmas) {
      final result = await addWord(lemma, language, source: source);
      if (result > 0) added++;
    }
    return added;
  }

  /// Remove a word from known words
  Future<void> removeWord(int wordId) async {
    await _db.softDelete('known_words', wordId);
  }

  /// Check if a word is known
  Future<bool> isWordKnown(String lemma, String language) async {
    final db = await _db.database;
    
    final result = await db.query(
      'known_words',
      where: 'lemma = ? AND language = ? AND deleted_at IS NULL',
      whereArgs: [lemma.toLowerCase(), language],
    );

    return result.isNotEmpty;
  }

  /// Get all known words for a language
  Future<List<KnownWord>> getKnownWords(String language) async {
    final db = await _db.database;
    
    final result = await db.query(
      'known_words',
      where: 'language = ? AND deleted_at IS NULL',
      whereArgs: [language],
      orderBy: 'added_at DESC',
    );

    return result.map((json) => KnownWord.fromJson(json)).toList();
  }

  /// Get known word count for a language
  Future<int> getKnownWordCount(String language) async {
    final db = await _db.database;
    
    final result = await db.rawQuery(
      'SELECT COUNT(*) as count FROM known_words WHERE language = ? AND deleted_at IS NULL',
      [language],
    );

    return result.first['count'] as int;
  }

  /// Search known words
  Future<List<KnownWord>> searchKnownWords(
    String query,
    String language,
  ) async {
    final db = await _db.database;
    
    final result = await db.query(
      'known_words',
      where: 'language = ? AND lemma LIKE ? AND deleted_at IS NULL',
      whereArgs: [language, '%${query.toLowerCase()}%'],
      orderBy: 'lemma ASC',
    );

    return result.map((json) => KnownWord.fromJson(json)).toList();
  }

  /// Import words from text (extracts unique words)
  Future<int> importFromText(String text, String language) async {
    // Simple word extraction (split by whitespace and punctuation)
    final words = text
        .toLowerCase()
        .replaceAll(RegExp(r'[^\w\s]'), ' ')
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty && w.length > 1)
        .toSet()
        .toList();

    return await addWordsBulk(words, language, source: 'import');
  }

  /// Export known words as text
  Future<String> exportWords(String language) async {
    final words = await getKnownWords(language);
    return words.map((w) => w.lemma).join('\n');
  }

  /// Auto-add words from mastered flashcards
  Future<int> syncFromFlashcards(String language) async {
    final db = await _db.database;
    
    // Get mastered flashcards (easiness > 2.5, interval > 30)
    final result = await db.rawQuery('''
      SELECT DISTINCT f.question, f.answer
      FROM flashcards f
      JOIN decks d ON f.deck_id = d.id
      WHERE d.language = ?
        AND f.easiness > 2.5
        AND f.interval > 30
        AND f.deleted_at IS NULL
        AND d.deleted_at IS NULL
    ''', [language]);

    int added = 0;
    for (var row in result) {
      final question = row['question'] as String;
      final answer = row['answer'] as String;
      
      // Extract words from question and answer
      final words = '$question $answer'
          .toLowerCase()
          .replaceAll(RegExp(r'[^\w\s]'), ' ')
          .split(RegExp(r'\s+'))
          .where((w) => w.isNotEmpty && w.length > 1)
          .toSet();

      for (var word in words) {
        final result = await addWord(word, language, source: 'flashcard');
        if (result > 0) added++;
      }
    }

    return added;
  }

  /// Get known words by source
  Future<List<KnownWord>> getKnownWordsBySource(
    String language,
    String source,
  ) async {
    final db = await _db.database;
    
    final result = await db.query(
      'known_words',
      where: 'language = ? AND source = ? AND deleted_at IS NULL',
      whereArgs: [language, source],
      orderBy: 'added_at DESC',
    );

    return result.map((json) => KnownWord.fromJson(json)).toList();
  }
}
