/// Models for AI-generated suggestions
/// 
/// These models represent vocabulary flashcards and grammar patterns
/// extracted from AI responses.

import 'dart:convert';

/// Container for all types of suggestions
class Suggestions {
  final List<FlashcardSuggestion> flashcards;
  final List<GrammarSuggestion> grammar;
  
  const Suggestions({
    this.flashcards = const [],
    this.grammar = const [],
  });
  
  /// Check if there are no suggestions
  bool get isEmpty => flashcards.isEmpty && grammar.isEmpty;
  
  /// Check if there are any suggestions
  bool get isNotEmpty => !isEmpty;
  
  /// Total count of all suggestions
  int get totalCount => flashcards.length + grammar.length;
  
  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'flashcards': flashcards.map((f) => f.toJson()).toList(),
      'grammar': grammar.map((g) => g.toJson()).toList(),
    };
  }
  
  /// Create from JSON
  factory Suggestions.fromJson(Map<String, dynamic> json) {
    return Suggestions(
      flashcards: (json['flashcards'] as List<dynamic>?)
          ?.map((item) => FlashcardSuggestion.fromJson(item as Map<String, dynamic>))
          .toList() ?? [],
      grammar: (json['grammar'] as List<dynamic>?)
          ?.map((item) => GrammarSuggestion.fromJson(item as Map<String, dynamic>))
          .toList() ?? [],
    );
  }
  
  /// Convert to JSON string
  String toJsonString() => jsonEncode(toJson());
  
  /// Create from JSON string
  factory Suggestions.fromJsonString(String jsonString) {
    try {
      final json = jsonDecode(jsonString) as Map<String, dynamic>;
      return Suggestions.fromJson(json);
    } catch (e) {
      // Return empty suggestions if parsing fails
      return const Suggestions();
    }
  }
  
  @override
  String toString() {
    return 'Suggestions(flashcards: ${flashcards.length}, grammar: ${grammar.length})';
  }
  
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    
    return other is Suggestions &&
        _listEquals(other.flashcards, flashcards) &&
        _listEquals(other.grammar, grammar);
  }
  
  @override
  int get hashCode => Object.hash(
    Object.hashAll(flashcards),
    Object.hashAll(grammar),
  );
  
  bool _listEquals<T>(List<T> a, List<T> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}

/// A vocabulary flashcard suggestion
class FlashcardSuggestion {
  final String word;
  final String definition;
  final String? context; // Optional: sentence where word appears
  
  const FlashcardSuggestion({
    required this.word,
    required this.definition,
    this.context,
  });
  
  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'word': word,
      'definition': definition,
      if (context != null) 'context': context,
    };
  }
  
  /// Create from JSON
  factory FlashcardSuggestion.fromJson(Map<String, dynamic> json) {
    return FlashcardSuggestion(
      word: json['word'] as String,
      definition: json['definition'] as String,
      context: json['context'] as String?,
    );
  }
  
  @override
  String toString() {
    return 'FlashcardSuggestion(word: $word, definition: $definition${context != null ? ', context: $context' : ''})';
  }
  
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    
    return other is FlashcardSuggestion &&
        other.word == word &&
        other.definition == definition &&
        other.context == context;
  }
  
  @override
  int get hashCode => Object.hash(word, definition, context);
}

/// A grammar pattern suggestion
class GrammarSuggestion {
  final String title;
  final String explanation;
  
  const GrammarSuggestion({
    required this.title,
    required this.explanation,
  });
  
  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'explanation': explanation,
    };
  }
  
  /// Create from JSON
  factory GrammarSuggestion.fromJson(Map<String, dynamic> json) {
    return GrammarSuggestion(
      title: json['title'] as String,
      explanation: json['explanation'] as String,
    );
  }
  
  @override
  String toString() {
    return 'GrammarSuggestion(title: $title, explanation: $explanation)';
  }
  
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    
    return other is GrammarSuggestion &&
        other.title == title &&
        other.explanation == explanation;
  }
  
  @override
  int get hashCode => Object.hash(title, explanation);
}
