/// Sentence Explanation Model
/// 
/// Represents an AI-generated explanation for a sentence with embedded suggestions.

import 'suggestions.dart';

class SentenceExplanation {
  final int id;
  final int importedContentId;
  final String sentence;
  final String explanation;
  final String explanationLanguage; // 'native' or language code
  final String source; // 'ai' or 'manual'
  final String focusArea; // 'all', 'grammar', 'vocabulary', 'context'
  final String createdAt;
  final String lastUpdated;
  final Suggestions? suggestions;
  
  const SentenceExplanation({
    required this.id,
    required this.importedContentId,
    required this.sentence,
    required this.explanation,
    required this.explanationLanguage,
    required this.source,
    required this.focusArea,
    required this.createdAt,
    required this.lastUpdated,
    this.suggestions,
  });
  
  /// Create from database row
  factory SentenceExplanation.fromMap(Map<String, dynamic> map) {
    return SentenceExplanation(
      id: map['id'] as int,
      importedContentId: map['imported_content_id'] as int,
      sentence: map['sentence'] as String,
      explanation: map['explanation'] as String,
      explanationLanguage: map['explanation_language'] as String,
      source: map['source'] as String,
      focusArea: map['focus_area'] as String? ?? 'all',
      createdAt: map['created_at'] as String,
      lastUpdated: map['last_updated'] as String,
      suggestions: map['grammar_notes'] != null 
          ? Suggestions.fromJsonString(map['grammar_notes'] as String)
          : null,
    );
  }
  
  /// Convert to database map
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'imported_content_id': importedContentId,
      'sentence': sentence,
      'explanation': explanation,
      'explanation_language': explanationLanguage,
      'source': source,
      'focus_area': focusArea,
      'created_at': createdAt,
      'last_updated': lastUpdated,
      if (suggestions != null) 'grammar_notes': suggestions!.toJsonString(),
    };
  }
}

/// Result of generating a sentence explanation
class SentenceExplanationResult {
  final int explanationId;
  final String explanation;
  final Suggestions suggestions;
  
  const SentenceExplanationResult({
    required this.explanationId,
    required this.explanation,
    required this.suggestions,
  });
}
