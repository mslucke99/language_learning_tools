import 'dart:math';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class QuizService {
  final DatabaseHelper _db = DatabaseHelper();
  final Random _random = Random();

  /// Generate a new quiz from a deck
  Future<int> generateQuiz({
    required String sourceType,
    required int sourceId,
    required int questionCount,
    required String difficulty,
  }) async {
    // Fetch items based on source
    final items = await _fetchQuizItems(sourceType, sourceId);
    
    if (items.isEmpty) {
      throw Exception('No items available for quiz');
    }
    
    // Randomly select items
    final selectedCount = min(questionCount, items.length);
    final selected = (items.toList()..shuffle(_random)).take(selectedCount).toList();
    
    // Create session
    final now = DateTime.now().toIso8601String();
    final sessionId = await _db.insertItem('quiz_sessions', {
      'source_type': sourceType,
      'source_id': sourceId,
      'question_count': selected.length,
      'difficulty': difficulty,
      'score': 0,
      'total_questions': selected.length,
      'created_at': now,
    });
    
    // Generate questions
    for (final item in selected) {
      await _createQuestion(sessionId, item, sourceType, difficulty, items);
    }
    
    return sessionId;
  }

  /// Fetch items for quiz based on source type
  Future<List<Map<String, dynamic>>> _fetchQuizItems(
    String sourceType,
    int sourceId,
  ) async {
    final db = await _db.database;
    
    if (sourceType == 'deck') {
      // Fetch flashcards from deck
      final result = await db.query(
        'flashcards',
        where: 'deck_id = ? AND deleted_at IS NULL',
        whereArgs: [sourceId],
      );
      
      return result.map((row) => {
        'question': row['question'],
        'answer': row['answer'],
        'type': 'flashcard',
      }).toList();
    } else if (sourceType == 'vocab') {
      // Fetch vocabulary from imported content
      final result = await db.query(
        'imported_content',
        where: 'content_type = ? AND collection_id = ? AND deleted_at IS NULL',
        whereArgs: ['word', sourceId],
      );
      
      return result.map((row) => {
        'question': row['content'],
        'answer': row['context'] ?? 'Definition',
        'type': 'vocab',
      }).toList();
    } else if (sourceType == 'grammar') {
      // Fetch grammar entries
      final result = await db.query(
        'grammar_book_entries',
        where: 'collection_id = ? AND deleted_at IS NULL',
        whereArgs: [sourceId],
      );
      
      return result.map((row) => {
        'question': row['title'],
        'answer': row['content'],
        'type': 'grammar',
      }).toList();
    }
    
    return [];
  }

  /// Create a multiple choice question
  Future<void> _createQuestion(
    int sessionId,
    Map<String, dynamic> item,
    String sourceType,
    String difficulty,
    List<Map<String, dynamic>> allItems,
  ) async {
    final questionText = item['question'] as String;
    final correctAnswer = item['answer'] as String;
    
    // Generate distractors (wrong answers)
    final distractors = _generateDistractors(
      correctAnswer,
      difficulty,
      allItems,
      item,
    );
    
    // Shuffle choices
    final allChoices = [correctAnswer, ...distractors];
    allChoices.shuffle(_random);
    
    // Ensure we have exactly 4 choices
    while (allChoices.length < 4) {
      allChoices.add('Option ${allChoices.length + 1}');
    }
    
    // Assign to A, B, C, D
    final choices = {
      'A': allChoices[0],
      'B': allChoices[1],
      'C': allChoices[2],
      'D': allChoices[3],
    };
    
    // Find correct letter
    final correctLetter = choices.entries
        .firstWhere((entry) => entry.value == correctAnswer)
        .key;
    
    // Save question
    await _db.insertItem('quiz_questions', {
      'session_id': sessionId,
      'question_text': questionText,
      'correct_answer': correctLetter,
      'choice_a': choices['A'],
      'choice_b': choices['B'],
      'choice_c': choices['C'],
      'choice_d': choices['D'],
    });
  }

  /// Generate wrong answers (distractors)
  List<String> _generateDistractors(
    String correctAnswer,
    String difficulty,
    List<Map<String, dynamic>> allItems,
    Map<String, dynamic> currentItem,
  ) {
    // Get other answers from the same item pool
    final otherAnswers = allItems
        .where((item) => item['answer'] != correctAnswer)
        .map((item) => item['answer'] as String)
        .toList();
    
    if (otherAnswers.isEmpty) {
      // Fallback: generate generic distractors
      return [
        'Option A',
        'Option B',
        'Option C',
      ];
    }
    
    // Shuffle and take 3
    otherAnswers.shuffle(_random);
    return otherAnswers.take(3).toList();
  }

  /// Submit an answer for a question
  Future<bool> submitAnswer(int questionId, String userAnswer) async {
    final db = await _db.database;
    
    // Get the question
    final result = await db.query(
      'quiz_questions',
      where: 'id = ?',
      whereArgs: [questionId],
    );
    
    if (result.isEmpty) {
      throw Exception('Question not found');
    }
    
    final question = QuizQuestion.fromJson(result.first);
    final correctAnswer = question.correctAnswer;
    final isCorrect = userAnswer == correctAnswer;
    
    // Update question with user answer
    await _db.updateItem('quiz_questions', questionId, {
      'user_answer': userAnswer,
      'is_correct': isCorrect ? 1 : 0,
    });
    
    return isCorrect;
  }

  /// Calculate and update final score for a session
  Future<int> calculateScore(int sessionId) async {
    final db = await _db.database;
    
    // Count correct answers
    final result = await db.rawQuery('''
      SELECT COUNT(*) as correct
      FROM quiz_questions
      WHERE session_id = ? AND is_correct = 1
    ''', [sessionId]);
    
    final correct = result.first['correct'] as int;
    
    // Get total questions
    final sessionResult = await db.query(
      'quiz_sessions',
      where: 'id = ?',
      whereArgs: [sessionId],
    );
    
    if (sessionResult.isEmpty) {
      throw Exception('Session not found');
    }
    
    final session = QuizSession.fromJson(sessionResult.first);
    final total = session.totalQuestions ?? 0;
    
    // Calculate score percentage
    final score = total > 0 ? ((correct / total) * 100).round() : 0;
    
    // Update session
    await _db.updateItem('quiz_sessions', sessionId, {
      'score': score,
    });
    
    return score;
  }

  /// Get all questions for a quiz session
  Future<List<QuizQuestion>> getQuizQuestions(int sessionId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'quiz_questions',
      where: 'session_id = ? AND deleted_at IS NULL',
      whereArgs: [sessionId],
      orderBy: 'id ASC',
    );
    
    return result.map((json) => QuizQuestion.fromJson(json)).toList();
  }

  /// Get quiz session details
  Future<QuizSession?> getQuizSession(int sessionId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'quiz_sessions',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [sessionId],
    );
    
    if (result.isEmpty) {
      return null;
    }
    
    return QuizSession.fromJson(result.first);
  }

  /// Get all quiz sessions
  Future<List<QuizSession>> getAllQuizSessions() async {
    final db = await _db.database;
    
    final result = await db.query(
      'quiz_sessions',
      where: 'deleted_at IS NULL',
      orderBy: 'created_at DESC',
    );
    
    return result.map((json) => QuizSession.fromJson(json)).toList();
  }

  /// Get quiz results with questions
  Future<Map<String, dynamic>> getQuizResults(int sessionId) async {
    final session = await getQuizSession(sessionId);
    final questions = await getQuizQuestions(sessionId);
    
    if (session == null) {
      throw Exception('Session not found');
    }
    
    return {
      'session': session,
      'questions': questions,
      'score': session.score ?? 0,
      'total': session.totalQuestions ?? 0,
    };
  }
}
