import 'dart:convert';
import 'database_helper.dart';
import 'llm_service.dart';
import 'prompts.dart';
import '../models/models.dart';

class GrammarService {
  final DatabaseHelper _db = DatabaseHelper();
  final LLMService _llmService;

  GrammarService(this._llmService);

  /// Create a new grammar entry
  Future<int> createEntry({
    required String title,
    required String content,
    String? language,
    String? tags,
    int? proficiency,
    int? collectionId,
  }) async {
    final now = DateTime.now().toIso8601String();

    return await _db.insertItem('grammar_book_entries', {
      'title': title,
      'content': content,
      'language': language,
      'tags': tags,
      'proficiency': proficiency ?? 0,
      'collection_id': collectionId,
      'created_at': now,
      'updated_at': now,
    });
  }

  /// Update an existing grammar entry
  Future<void> updateEntry(
    int id, {
    String? title,
    String? content,
    String? language,
    String? tags,
    int? proficiency,
    int? collectionId,
  }) async {
    final now = DateTime.now().toIso8601String();
    final Map<String, dynamic> data = {'updated_at': now};

    if (title != null) data['title'] = title;
    if (content != null) data['content'] = content;
    if (language != null) data['language'] = language;
    if (tags != null) data['tags'] = tags;
    if (proficiency != null) data['proficiency'] = proficiency;
    if (collectionId != null) data['collection_id'] = collectionId;

    await _db.updateItem('grammar_book_entries', id, data);
  }

  /// Delete a grammar entry (soft delete)
  Future<void> deleteEntry(int id) async {
    await _db.softDelete('grammar_book_entries', id);
  }

  /// Get all grammar entries
  Future<List<GrammarBookEntry>> getEntries({
    String? language,
    int? minProficiency,
    int? maxProficiency,
    int? collectionId,
  }) async {
    final db = await _db.database;

    String whereClause = 'deleted_at IS NULL';
    List<dynamic> whereArgs = [];

    if (language != null) {
      whereClause += ' AND language = ?';
      whereArgs.add(language);
    }

    if (minProficiency != null) {
      whereClause += ' AND proficiency >= ?';
      whereArgs.add(minProficiency);
    }

    if (maxProficiency != null) {
      whereClause += ' AND proficiency <= ?';
      whereArgs.add(maxProficiency);
    }

    if (collectionId != null) {
      whereClause += ' AND collection_id = ?';
      whereArgs.add(collectionId);
    }

    final result = await db.query(
      'grammar_book_entries',
      where: whereClause,
      whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
      orderBy: 'proficiency ASC, title ASC',
    );

    return result.map((json) => GrammarBookEntry.fromJson(json)).toList();
  }

  /// Get a single grammar entry
  Future<GrammarBookEntry?> getEntry(int id) async {
    final db = await _db.database;

    final result = await db.query(
      'grammar_book_entries',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [id],
    );

    if (result.isEmpty) return null;
    return GrammarBookEntry.fromJson(result.first);
  }

  /// Get entries by collection
  Future<List<GrammarBookEntry>> getEntriesByCollection(
    int collectionId,
  ) async {
    final db = await _db.database;

    final result = await db.query(
      'grammar_book_entries',
      where: 'collection_id = ? AND deleted_at IS NULL',
      whereArgs: [collectionId],
      orderBy: 'updated_at DESC',
    );

    return result.map((json) => GrammarBookEntry.fromJson(json)).toList();
  }

  /// Get entries by proficiency level
  Future<List<GrammarBookEntry>> getEntriesByProficiency(
    int proficiency,
  ) async {
    final db = await _db.database;

    final result = await db.query(
      'grammar_book_entries',
      where: 'proficiency = ? AND deleted_at IS NULL',
      whereArgs: [proficiency],
      orderBy: 'updated_at DESC',
    );

    return result.map((json) => GrammarBookEntry.fromJson(json)).toList();
  }

  /// Generate grammar practice sentences based on mastered patterns
  Future<List<Map<String, dynamic>>> generateGrammarPractice(
    String studyLanguage,
    String nativeLanguage,
    int count,
  ) async {
    final db = await _db.database;

    // Fetch mastered grammar patterns (proficiency >= 4, which is "Advanced" or "Mastered" in our 0-5 scale)
    // Actually our scale is 0-5 now, let's say >= 4.
    final patterns = await db.query(
      'grammar_book_entries',
      where: 'language = ? AND proficiency >= 4 AND deleted_at IS NULL',
      whereArgs: [studyLanguage],
      limit: 10,
    );

    if (patterns.isEmpty) {
      throw Exception('No mastered grammar patterns found to practice.');
    }

    final patternTitles = patterns.map((p) => p['title'].toString()).join(', ');
    final template = Prompts.practicePrompts['grammar_practice']!['template']!;

    final prompt = Prompts.format(template, {
      'count': count.toString(),
      'patterns': patternTitles,
      'study_language': studyLanguage,
      'native_language': nativeLanguage,
    });

    final response = await _llmService.generate(prompt);
    if (response == null) throw Exception('Failed to generate practice');

    final jsonStart = response.indexOf('{');
    final jsonEnd = response.lastIndexOf('}') + 1;

    if (jsonStart != -1 && jsonEnd > jsonStart) {
      final jsonStr = response.substring(jsonStart, jsonEnd);
      final data = json.decode(jsonStr);
      return List<Map<String, dynamic>>.from(data['sentences'] ?? []);
    }

    return [];
  }
}
