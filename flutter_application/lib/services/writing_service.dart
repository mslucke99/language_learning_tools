import 'dart:convert';
import '../models/models.dart';
import 'database_helper.dart';
import 'llm_service.dart';
import 'prompts.dart';

class WritingService {
  final DatabaseHelper _db = DatabaseHelper();
  final LLMService _llmService;

  WritingService(this._llmService);

  /// Create a new writing session
  Future<int> createSession(String topic, String language) async {
    final now = DateTime.now().toIso8601String();

    return await _db.insertItem('writing_sessions', {
      'topic': topic,
      'user_writing': '',
      'study_language': language,
      'created_at': now,
    });
  }

  /// Submit writing for AI feedback
  Future<Map<String, dynamic>> submitForFeedback(
    int sessionId,
    String text,
    String language,
    String topic,
  ) async {
    final template = Prompts.writingPrompts['grade']!['template']!;
    final prompt = Prompts.format(template, {
      'topic': topic,
      'user_writing': text,
      'study_language': language,
      'native_language': 'English', // TODO: Get from settings
    });

    final response = await _llmService.generate(prompt);

    if (response == null) {
      throw Exception('Failed to get feedback from LLM');
    }

    // Parse for structured suggestions (flashcards, grammar)
    final parsed = LLMService.parseAISuggestions(response);
    final analysis = _parseFeedbackResponse(parsed['cleanText']);

    // Merge suggestions into analysis
    analysis['suggestions_data'] = parsed['suggestions'];

    return analysis;
  }

  /// Save writing session with feedback
  Future<void> saveSession(
    int sessionId,
    String text,
    String? feedback,
    String? grade,
    String? analysis,
  ) async {
    await _db.updateItem('writing_sessions', sessionId, {
      'user_writing': text,
      'feedback': feedback,
      'grade': grade,
      'analysis': analysis,
    });
  }

  /// Get all writing sessions
  Future<List<WritingSession>> getSessions({String? language}) async {
    final db = await _db.database;

    String whereClause = 'deleted_at IS NULL';
    List<dynamic> whereArgs = [];

    if (language != null) {
      whereClause += ' AND study_language = ?';
      whereArgs.add(language);
    }

    final result = await db.query(
      'writing_sessions',
      where: whereClause,
      whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
      orderBy: 'created_at DESC',
    );

    return result.map((json) => WritingSession.fromJson(json)).toList();
  }

  /// Get a single writing session
  Future<WritingSession?> getSession(int sessionId) async {
    final db = await _db.database;

    final result = await db.query(
      'writing_sessions',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [sessionId],
    );

    if (result.isEmpty) return null;
    return WritingSession.fromJson(result.first);
  }

  /// Delete a writing session
  Future<void> deleteSession(int sessionId) async {
    await _db.softDelete('writing_sessions', sessionId);
  }

  /// Parse feedback response from LLM
  Map<String, dynamic> _parseFeedbackResponse(String response) {
    try {
      // Try to extract JSON from response first (if any)
      final jsonStart = response.indexOf('{');
      final jsonEnd = response.lastIndexOf('}') + 1;

      if (jsonStart != -1 && jsonEnd > jsonStart) {
        final jsonStr = response.substring(jsonStart, jsonEnd);
        return json.decode(jsonStr);
      }

      // If no JSON found, return raw feedback in a structured way
      return {
        'grade': 'N/A',
        'strengths': [],
        'improvements': [],
        'suggestions': [],
        'vocabulary': [],
        'raw_feedback': response,
      };
    } catch (e) {
      return {
        'grade': 'N/A',
        'strengths': [],
        'improvements': [],
        'suggestions': [],
        'vocabulary': [],
        'raw_feedback': response,
        'error': e.toString(),
      };
    }
  }
}
