// GENERATED CODE - DO NOT MODIFY BY HAND

class Deck {
  final int? id;
  final String name;
  final String createdAt;
  final String? description;
  final int? collectionId;
  final String? language;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  Deck({
    this.id,
    required this.name,
    required this.createdAt,
    this.description,
    this.collectionId,
    this.language,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory Deck.fromJson(Map<String, dynamic> json) {
    return Deck(
      id: json['id'],
      name: json['name'],
      createdAt: json['created_at'],
      description: json['description'],
      collectionId: json['collection_id'],
      language: json['language'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'created_at': createdAt,
        'description': description,
        'collection_id': collectionId,
        'language': language,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class Flashcard {
  final int? id;
  final int deckId;
  final String question;
  final String answer;
  final String? lastReviewed;
  final double? easiness;
  final int? interval;
  final int? repetitions;
  final int? totalReviews;
  final int? correctReviews;
  final String? userNotes;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  Flashcard({
    this.id,
    required this.deckId,
    required this.question,
    required this.answer,
    this.lastReviewed,
    this.easiness,
    this.interval,
    this.repetitions,
    this.totalReviews,
    this.correctReviews,
    this.userNotes,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory Flashcard.fromJson(Map<String, dynamic> json) {
    return Flashcard(
      id: json['id'],
      deckId: json['deck_id'],
      question: json['question'],
      answer: json['answer'],
      lastReviewed: json['last_reviewed'],
      easiness: json['easiness'],
      interval: json['interval'],
      repetitions: json['repetitions'],
      totalReviews: json['total_reviews'],
      correctReviews: json['correct_reviews'],
      userNotes: json['user_notes'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'deck_id': deckId,
        'question': question,
        'answer': answer,
        'last_reviewed': lastReviewed,
        'easiness': easiness,
        'interval': interval,
        'repetitions': repetitions,
        'total_reviews': totalReviews,
        'correct_reviews': correctReviews,
        'user_notes': userNotes,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ImportedContent {
  final int? id;
  final String contentType;
  final String content;
  final String? context;
  final String? title;
  final String url;
  final String? language;
  final String createdAt;
  final int? processed;
  final String? tags;
  final int? collectionId;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ImportedContent({
    this.id,
    required this.contentType,
    required this.content,
    this.context,
    this.title,
    required this.url,
    this.language,
    required this.createdAt,
    this.processed,
    this.tags,
    this.collectionId,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ImportedContent.fromJson(Map<String, dynamic> json) {
    return ImportedContent(
      id: json['id'],
      contentType: json['content_type'],
      content: json['content'],
      context: json['context'],
      title: json['title'],
      url: json['url'],
      language: json['language'],
      createdAt: json['created_at'],
      processed: json['processed'],
      tags: json['tags'],
      collectionId: json['collection_id'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'content_type': contentType,
        'content': content,
        'context': context,
        'title': title,
        'url': url,
        'language': language,
        'created_at': createdAt,
        'processed': processed,
        'tags': tags,
        'collection_id': collectionId,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class WordDefinition {
  final int? id;
  final int importedContentId;
  final String word;
  final String definition;
  final String? definitionLanguage;
  final String? source;
  final String createdAt;
  final String lastUpdated;
  final String? examples;
  final String? notes;
  final int? difficultyLevel;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  WordDefinition({
    this.id,
    required this.importedContentId,
    required this.word,
    required this.definition,
    this.definitionLanguage,
    this.source,
    required this.createdAt,
    required this.lastUpdated,
    this.examples,
    this.notes,
    this.difficultyLevel,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory WordDefinition.fromJson(Map<String, dynamic> json) {
    return WordDefinition(
      id: json['id'],
      importedContentId: json['imported_content_id'],
      word: json['word'],
      definition: json['definition'],
      definitionLanguage: json['definition_language'],
      source: json['source'],
      createdAt: json['created_at'],
      lastUpdated: json['last_updated'],
      examples: json['examples'],
      notes: json['notes'],
      difficultyLevel: json['difficulty_level'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'imported_content_id': importedContentId,
        'word': word,
        'definition': definition,
        'definition_language': definitionLanguage,
        'source': source,
        'created_at': createdAt,
        'last_updated': lastUpdated,
        'examples': examples,
        'notes': notes,
        'difficulty_level': difficultyLevel,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class SentenceExplanation {
  final int? id;
  final int importedContentId;
  final String sentence;
  final String explanation;
  final String? explanationLanguage;
  final String? source;
  final String? focusArea;
  final String createdAt;
  final String lastUpdated;
  final String? grammarNotes;
  final String? userNotes;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  SentenceExplanation({
    this.id,
    required this.importedContentId,
    required this.sentence,
    required this.explanation,
    this.explanationLanguage,
    this.source,
    this.focusArea,
    required this.createdAt,
    required this.lastUpdated,
    this.grammarNotes,
    this.userNotes,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory SentenceExplanation.fromJson(Map<String, dynamic> json) {
    return SentenceExplanation(
      id: json['id'],
      importedContentId: json['imported_content_id'],
      sentence: json['sentence'],
      explanation: json['explanation'],
      explanationLanguage: json['explanation_language'],
      source: json['source'],
      focusArea: json['focus_area'],
      createdAt: json['created_at'],
      lastUpdated: json['last_updated'],
      grammarNotes: json['grammar_notes'],
      userNotes: json['user_notes'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'imported_content_id': importedContentId,
        'sentence': sentence,
        'explanation': explanation,
        'explanation_language': explanationLanguage,
        'source': source,
        'focus_area': focusArea,
        'created_at': createdAt,
        'last_updated': lastUpdated,
        'grammar_notes': grammarNotes,
        'user_notes': userNotes,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class GrammarBookEntry {
  final int? id;
  final String title;
  final String content;
  final String? language;
  final String? tags;
  final String createdAt;
  final String? updatedAt;
  final int? collectionId;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  GrammarBookEntry({
    this.id,
    required this.title,
    required this.content,
    this.language,
    this.tags,
    required this.createdAt,
    this.updatedAt,
    this.collectionId,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory GrammarBookEntry.fromJson(Map<String, dynamic> json) {
    return GrammarBookEntry(
      id: json['id'],
      title: json['title'],
      content: json['content'],
      language: json['language'],
      tags: json['tags'],
      createdAt: json['created_at'],
      updatedAt: json['updated_at'],
      collectionId: json['collection_id'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'content': content,
        'language': language,
        'tags': tags,
        'created_at': createdAt,
        'updated_at': updatedAt,
        'collection_id': collectionId,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class PendingSyncAction {
  final int? id;
  final String actionType;
  final String? targetTable;
  final int? targetId;
  final String? payload;
  final String? status;
  final String createdAt;
  final String? processedAt;

  PendingSyncAction({
    this.id,
    required this.actionType,
    this.targetTable,
    this.targetId,
    this.payload,
    this.status,
    required this.createdAt,
    this.processedAt,
  });

  factory PendingSyncAction.fromJson(Map<String, dynamic> json) {
    return PendingSyncAction(
      id: json['id'],
      actionType: json['action_type'],
      targetTable: json['target_table'],
      targetId: json['target_id'],
      payload: json['payload'],
      status: json['status'],
      createdAt: json['created_at'],
      processedAt: json['processed_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'action_type': actionType,
        'target_table': targetTable,
        'target_id': targetId,
        'payload': payload,
        'status': status,
        'created_at': createdAt,
        'processed_at': processedAt,
      };
}

