/// Grammar Follow-up Model
/// 
/// Represents a Q&A pair for follow-up questions about sentence explanations.

class GrammarFollowup {
  final int id;
  final int sentenceExplanationId;
  final String question;
  final String answer;
  final String context;
  final String createdAt;
  
  const GrammarFollowup({
    required this.id,
    required this.sentenceExplanationId,
    required this.question,
    required this.answer,
    required this.context,
    required this.createdAt,
  });
  
  /// Create from database row
  factory GrammarFollowup.fromMap(Map<String, dynamic> map) {
    return GrammarFollowup(
      id: map['id'] as int,
      sentenceExplanationId: map['sentence_explanation_id'] as int,
      question: map['question'] as String,
      answer: map['answer'] as String,
      context: map['context'] as String,
      createdAt: map['created_at'] as String,
    );
  }
  
  /// Convert to database map
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'sentence_explanation_id': sentenceExplanationId,
      'question': question,
      'answer': answer,
      'context': context,
      'created_at': createdAt,
    };
  }
}
