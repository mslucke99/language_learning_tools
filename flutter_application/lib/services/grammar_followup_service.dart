/// Grammar Follow-up Service
/// 
/// Manages follow-up questions and answers about sentence explanations.
/// Maintains context across multiple Q&A exchanges.

import '../models/grammar_followup.dart';
import 'database_helper.dart';
import 'llm_service.dart';

class GrammarFollowupService {
  final DatabaseHelper _db;
  final LLMService _llm;
  
  GrammarFollowupService(this._db, this._llm);
  
  /// Ask a follow-up question about a sentence explanation
  Future<GrammarFollowup> askFollowup({
    required int sentenceExplanationId,
    required String question,
    required String sentence,
    required String explanation,
    required String language,
  }) async {
    // 1. Get previous follow-ups for context
    final previousFollowups = await getFollowups(sentenceExplanationId);
    
    // 2. Build context-aware prompt
    final prompt = _buildFollowupPrompt(
      sentence,
      explanation,
      previousFollowups,
      question,
      language,
    );
    
    // 3. Call LLM
    final answer = await _llm.generate(prompt);
    if (answer == null || answer.isEmpty) {
      throw Exception('Failed to generate answer');
    }
    
    // 4. Save to database
    final now = DateTime.now().toIso8601String();
    final id = await _db.insertItem('grammar_followups', {
      'sentence_explanation_id': sentenceExplanationId,
      'question': question,
      'answer': answer,
      'context': sentence,
      'created_at': now,
    });
    
    // 5. Return followup
    return GrammarFollowup(
      id: id,
      sentenceExplanationId: sentenceExplanationId,
      question: question,
      answer: answer,
      context: sentence,
      createdAt: now,
    );
  }
  
  /// Get all follow-ups for an explanation
  Future<List<GrammarFollowup>> getFollowups(int sentenceExplanationId) async {
    final db = await _db.database;
    
    final results = await db.query(
      'grammar_followups',
      where: 'sentence_explanation_id = ?',
      whereArgs: [sentenceExplanationId],
      orderBy: 'created_at ASC',
    );
    
    return results.map((row) => GrammarFollowup.fromMap(row)).toList();
  }
  
  /// Build context-aware prompt for follow-up question
  String _buildFollowupPrompt(
    String sentence,
    String explanation,
    List<GrammarFollowup> previousFollowups,
    String newQuestion,
    String language,
  ) {
    final studyLang = _getLanguageName(language);
    
    final buffer = StringBuffer();
    buffer.writeln('You are a $studyLang tutor helping a student understand grammar.');
    buffer.writeln();
    buffer.writeln('Original sentence: "$sentence"');
    buffer.writeln();
    buffer.writeln('Original explanation:');
    buffer.writeln(explanation);
    buffer.writeln();
    
    if (previousFollowups.isNotEmpty) {
      buffer.writeln('Previous Q&A:');
      for (int i = 0; i < previousFollowups.length; i++) {
        final followup = previousFollowups[i];
        buffer.writeln('Q${i + 1}: ${followup.question}');
        buffer.writeln('A${i + 1}: ${followup.answer}');
        buffer.writeln();
      }
    }
    
    buffer.writeln('New question from student: $newQuestion');
    buffer.writeln();
    buffer.writeln('Provide a clear, helpful answer in English. Reference the original sentence and previous discussion when relevant. Be specific and provide examples.');
    
    return buffer.toString();
  }
  
  /// Get language name from code
  String _getLanguageName(String code) {
    const languageNames = {
      'es': 'Spanish',
      'fr': 'French',
      'de': 'German',
      'it': 'Italian',
      'pt': 'Portuguese',
      'ja': 'Japanese',
      'ko': 'Korean',
      'zh': 'Chinese',
    };
    
    return languageNames[code] ?? code;
  }
}
