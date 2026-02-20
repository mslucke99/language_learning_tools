import 'dart:convert';
import '../models/models.dart';
import 'database_helper.dart';
import 'llm_service.dart';
import 'prompts.dart';

class ExamService {
  final DatabaseHelper _db = DatabaseHelper();
  final LLMService _llmService;

  ExamService(this._llmService);

  /// Generate an exam practice session
  Future<int> generateExam({
    required String examName,
    required String level,
    required String section,
    required int questionCount,
    required String language,
  }) async {
    final now = DateTime.now().toIso8601String();

    // Create exam attempt
    final attemptId = await _db.insertItem('exam_attempts', {
      'exam_name': examName,
      'level': level,
      'section': section,
      'total_questions': questionCount,
      'created_at': now,
    });

    // Generate questions using LLM
    final questions = await _generateQuestions(
      examName,
      level,
      section,
      questionCount,
      language,
    );

    // Save questions
    for (var question in questions) {
      await _db.insertItem('exam_questions', {
        'attempt_id': attemptId,
        'question_text': question['question'],
        'correct_answer': question['correct'],
        'choice_a': question['choices'][0],
        'choice_b': question['choices'][1],
        'choice_c': question['choices'][2],
        'choice_d': question['choices'][3],
        'explanation': question['explanation'],
      });
    }

    return attemptId;
  }

  /// Submit an answer for a question
  Future<bool> submitAnswer(int questionId, String answer) async {
    final db = await _db.database;

    // Get the question
    final result = await db.query(
      'exam_questions',
      where: 'id = ?',
      whereArgs: [questionId],
    );

    if (result.isEmpty) return false;

    final question = ExamQuestion.fromJson(result.first);
    final isCorrect = answer == question.correctAnswer ? 1 : 0;

    // Update question with user answer
    await _db.updateItem('exam_questions', questionId, {
      'user_answer': answer,
      'is_correct': isCorrect,
    });

    return isCorrect == 1;
  }

  /// Calculate final score for an exam attempt
  Future<int> calculateScore(int attemptId) async {
    final db = await _db.database;

    final result = await db.rawQuery(
      '''
      SELECT COUNT(*) as correct
      FROM exam_questions
      WHERE attempt_id = ? AND is_correct = 1
    ''',
      [attemptId],
    );

    final score = result.first['correct'] as int;

    // Update exam attempt with score
    await _db.updateItem('exam_attempts', attemptId, {'score': score});

    return score;
  }

  /// Get exam results
  Future<Map<String, dynamic>> getExamResults(int attemptId) async {
    final db = await _db.database;

    // Get attempt
    final attemptResult = await db.query(
      'exam_attempts',
      where: 'id = ?',
      whereArgs: [attemptId],
    );

    if (attemptResult.isEmpty) {
      throw Exception('Exam attempt not found');
    }

    final attempt = ExamAttempt.fromJson(attemptResult.first);

    // Get questions
    final questionsResult = await db.query(
      'exam_questions',
      where: 'attempt_id = ?',
      whereArgs: [attemptId],
      orderBy: 'id ASC',
    );

    final questions = questionsResult
        .map((json) => ExamQuestion.fromJson(json))
        .toList();

    return {
      'attempt': attempt,
      'questions': questions,
      'score': attempt.score ?? 0,
      'total': attempt.totalQuestions ?? 0,
      'percentage':
          attempt.totalQuestions != null && attempt.totalQuestions! > 0
          ? (attempt.score! / attempt.totalQuestions! * 100)
          : 0.0,
    };
  }

  /// Get exam history
  Future<List<ExamAttempt>> getExamHistory({String? examName}) async {
    final db = await _db.database;

    String whereClause = 'deleted_at IS NULL';
    List<dynamic>? whereArgs;

    if (examName != null) {
      whereClause += ' AND exam_name = ?';
      whereArgs = [examName];
    }

    final result = await db.query(
      'exam_attempts',
      where: whereClause,
      whereArgs: whereArgs,
      orderBy: 'created_at DESC',
    );

    return result.map((json) => ExamAttempt.fromJson(json)).toList();
  }

  /// Get questions for an exam attempt
  Future<List<ExamQuestion>> getExamQuestions(int attemptId) async {
    final db = await _db.database;

    final result = await db.query(
      'exam_questions',
      where: 'attempt_id = ? AND deleted_at IS NULL',
      whereArgs: [attemptId],
      orderBy: 'id ASC',
    );

    return result.map((json) => ExamQuestion.fromJson(json)).toList();
  }

  /// Generate questions using LLM
  Future<List<Map<String, dynamic>>> _generateQuestions(
    String examName,
    String level,
    String section,
    int count,
    String language,
  ) async {
    final List<Map<String, dynamic>> questions = [];
    final template = Prompts.examPrompts['generate_question']!['template']!;

    for (int i = 0; i < count; i++) {
      try {
        final prompt = Prompts.format(template, {
          'exam_name': examName,
          'level': level,
          'section': section,
          'native_language': 'English', // TODO: Get from settings
          'study_language': language,
        });

        final response = await _llmService.generate(prompt);
        if (response == null) continue;

        // Extract JSON from response
        final jsonStart = response.indexOf('{');
        final jsonEnd = response.lastIndexOf('}') + 1;

        if (jsonStart != -1 && jsonEnd > jsonStart) {
          final jsonStr = response.substring(jsonStart, jsonEnd);
          final data = json.decode(jsonStr);

          // Map JSON fields to expected database structure
          questions.add({
            'question': data['question'] ?? '',
            'correct': data['correct_answer'] ?? '',
            'choices': data['options'] ?? [],
            'explanation': data['explanation'] ?? '',
          });
        }
      } catch (e) {
        print('Error generating question $i: $e');
      }
    }

    return questions;
  }

  /// Get exam types
  List<String> getExamTypes() {
    return ['JLPT', 'HSK', 'DELE', 'DELF', 'TOPIK', 'TestDaF'];
  }

  /// Get levels for exam type
  List<String> getLevelsForExam(String examName) {
    switch (examName) {
      case 'JLPT':
        return ['N5', 'N4', 'N3', 'N2', 'N1'];
      case 'HSK':
        return ['HSK 1', 'HSK 2', 'HSK 3', 'HSK 4', 'HSK 5', 'HSK 6'];
      case 'DELE':
      case 'DELF':
        return ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
      case 'TOPIK':
        return ['TOPIK I', 'TOPIK II'];
      case 'TestDaF':
        return ['TDN 3', 'TDN 4', 'TDN 5'];
      default:
        return ['Beginner', 'Intermediate', 'Advanced'];
    }
  }

  /// Get sections for exam type
  List<String> getSectionsForExam(String examName) {
    switch (examName) {
      case 'JLPT':
        return ['Vocabulary', 'Grammar', 'Reading', 'Listening'];
      case 'HSK':
        return ['Listening', 'Reading', 'Writing'];
      case 'DELE':
      case 'DELF':
        return ['Reading', 'Writing', 'Listening', 'Speaking'];
      case 'TOPIK':
        return ['Listening', 'Writing', 'Reading'];
      case 'TestDaF':
        return ['Reading', 'Listening', 'Writing', 'Speaking'];
      default:
        return ['Reading', 'Writing', 'Listening', 'Speaking'];
    }
  }
}
