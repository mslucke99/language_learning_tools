/// Word Definition Model
/// 
/// Represents a definition for a word in the word_definitions table.

import 'dart:convert';

class WordDefinition {
  final int? id;
  final int importedContentId;
  final String word;
  final String definition;
  final String? definitionLanguage;
  final String source; // 'user', 'ai', etc.
  final String createdAt;
  final String lastUpdated;
  final List<WordExample>? examples;
  final String? notes;
  final int difficultyLevel; // 0-5
  
  const WordDefinition({
    this.id,
    required this.importedContentId,
    required this.word,
    required this.definition,
    this.definitionLanguage,
    required this.source,
    required this.createdAt,
    required this.lastUpdated,
    this.examples,
    this.notes,
    this.difficultyLevel = 0,
  });
  
  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      'imported_content_id': importedContentId,
      'word': word,
      'definition': definition,
      if (definitionLanguage != null) 'definition_language': definitionLanguage,
      'source': source,
      'created_at': createdAt,
      'last_updated': lastUpdated,
      if (examples != null) 
        'examples': jsonEncode(examples!.map((e) => e.toJson()).toList()),
      if (notes != null) 'notes': notes,
      'difficulty_level': difficultyLevel,
    };
  }
  
  factory WordDefinition.fromJson(Map<String, dynamic> json) {
    List<WordExample>? examples;
    if (json['examples'] != null) {
      try {
        final examplesJson = json['examples'] is String
            ? jsonDecode(json['examples'] as String)
            : json['examples'];
        examples = (examplesJson as List<dynamic>)
            .map((e) => WordExample.fromJson(e as Map<String, dynamic>))
            .toList();
      } catch (e) {
        examples = null;
      }
    }
    
    return WordDefinition(
      id: json['id'] as int?,
      importedContentId: json['imported_content_id'] as int,
      word: json['word'] as String,
      definition: json['definition'] as String,
      definitionLanguage: json['definition_language'] as String?,
      source: json['source'] as String,
      createdAt: json['created_at'] as String,
      lastUpdated: json['last_updated'] as String,
      examples: examples,
      notes: json['notes'] as String?,
      difficultyLevel: json['difficulty_level'] as int? ?? 0,
    );
  }
  
  WordDefinition copyWith({
    int? id,
    int? importedContentId,
    String? word,
    String? definition,
    String? definitionLanguage,
    String? source,
    String? createdAt,
    String? lastUpdated,
    List<WordExample>? examples,
    String? notes,
    int? difficultyLevel,
  }) {
    return WordDefinition(
      id: id ?? this.id,
      importedContentId: importedContentId ?? this.importedContentId,
      word: word ?? this.word,
      definition: definition ?? this.definition,
      definitionLanguage: definitionLanguage ?? this.definitionLanguage,
      source: source ?? this.source,
      createdAt: createdAt ?? this.createdAt,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      examples: examples ?? this.examples,
      notes: notes ?? this.notes,
      difficultyLevel: difficultyLevel ?? this.difficultyLevel,
    );
  }
}

class WordExample {
  final String sentence;
  final String translation;
  
  const WordExample({
    required this.sentence,
    required this.translation,
  });
  
  Map<String, dynamic> toJson() => {
    'sentence': sentence,
    'translation': translation,
  };
  
  factory WordExample.fromJson(Map<String, dynamic> json) => WordExample(
    sentence: json['sentence'] as String,
    translation: json['translation'] as String,
  );
  
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is WordExample &&
        other.sentence == sentence &&
        other.translation == translation;
  }
  
  @override
  int get hashCode => Object.hash(sentence, translation);
}
