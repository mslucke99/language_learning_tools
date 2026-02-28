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
  final int? proficiency;
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
    this.proficiency,
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
      proficiency: json['proficiency'],
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
        'proficiency': proficiency,
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


class QuizSession {
  final int? id;
  final String sourceType;
  final int? sourceId;
  final int? questionCount;
  final String? difficulty;
  final int? score;
  final int? totalQuestions;
  final String createdAt;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  QuizSession({
    this.id,
    required this.sourceType,
    this.sourceId,
    this.questionCount,
    this.difficulty,
    this.score,
    this.totalQuestions,
    required this.createdAt,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory QuizSession.fromJson(Map<String, dynamic> json) {
    return QuizSession(
      id: json['id'],
      sourceType: json['source_type'],
      sourceId: json['source_id'],
      questionCount: json['question_count'],
      difficulty: json['difficulty'],
      score: json['score'],
      totalQuestions: json['total_questions'],
      createdAt: json['created_at'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_type': sourceType,
        'source_id': sourceId,
        'question_count': questionCount,
        'difficulty': difficulty,
        'score': score,
        'total_questions': totalQuestions,
        'created_at': createdAt,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class QuizQuestion {
  final int? id;
  final int sessionId;
  final String questionText;
  final String correctAnswer;
  final String? choiceA;
  final String? choiceB;
  final String? choiceC;
  final String? choiceD;
  final String? userAnswer;
  final int? isCorrect;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  QuizQuestion({
    this.id,
    required this.sessionId,
    required this.questionText,
    required this.correctAnswer,
    this.choiceA,
    this.choiceB,
    this.choiceC,
    this.choiceD,
    this.userAnswer,
    this.isCorrect,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory QuizQuestion.fromJson(Map<String, dynamic> json) {
    return QuizQuestion(
      id: json['id'],
      sessionId: json['session_id'],
      questionText: json['question_text'],
      correctAnswer: json['correct_answer'],
      choiceA: json['choice_a'],
      choiceB: json['choice_b'],
      choiceC: json['choice_c'],
      choiceD: json['choice_d'],
      userAnswer: json['user_answer'],
      isCorrect: json['is_correct'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'session_id': sessionId,
        'question_text': questionText,
        'correct_answer': correctAnswer,
        'choice_a': choiceA,
        'choice_b': choiceB,
        'choice_c': choiceC,
        'choice_d': choiceD,
        'user_answer': userAnswer,
        'is_correct': isCorrect,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ReviewLog {
  final int? id;
  final int flashcardId;
  final String? reviewDesc;
  final int? grade;
  final int? timeTaken;
  final String reviewDate;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ReviewLog({
    this.id,
    required this.flashcardId,
    this.reviewDesc,
    this.grade,
    this.timeTaken,
    required this.reviewDate,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ReviewLog.fromJson(Map<String, dynamic> json) {
    return ReviewLog(
      id: json['id'],
      flashcardId: json['flashcard_id'],
      reviewDesc: json['review_desc'],
      grade: json['grade'],
      timeTaken: json['time_taken'],
      reviewDate: json['review_date'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'flashcard_id': flashcardId,
        'review_desc': reviewDesc,
        'grade': grade,
        'time_taken': timeTaken,
        'review_date': reviewDate,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ChatSession {
  final int? id;
  final String? curTopic;
  final String? studyLanguage;
  final String? mode;
  final int? scenarioId;
  final String? characterContext;
  final String createdAt;
  final String lastUpdated;
  final String? userNotes;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ChatSession({
    this.id,
    this.curTopic,
    this.studyLanguage,
    this.mode,
    this.scenarioId,
    this.characterContext,
    required this.createdAt,
    required this.lastUpdated,
    this.userNotes,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    return ChatSession(
      id: json['id'],
      curTopic: json['cur_topic'],
      studyLanguage: json['study_language'],
      mode: json['mode'],
      scenarioId: json['scenario_id'],
      characterContext: json['character_context'],
      createdAt: json['created_at'],
      lastUpdated: json['last_updated'],
      userNotes: json['user_notes'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'cur_topic': curTopic,
        'study_language': studyLanguage,
        'mode': mode,
        'scenario_id': scenarioId,
        'character_context': characterContext,
        'created_at': createdAt,
        'last_updated': lastUpdated,
        'user_notes': userNotes,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ChatMessage {
  final int? id;
  final int sessionId;
  final String role;
  final String content;
  final String? analysis;
  final String createdAt;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ChatMessage({
    this.id,
    required this.sessionId,
    required this.role,
    required this.content,
    this.analysis,
    required this.createdAt,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'],
      sessionId: json['session_id'],
      role: json['role'],
      content: json['content'],
      analysis: json['analysis'],
      createdAt: json['created_at'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'session_id': sessionId,
        'role': role,
        'content': content,
        'analysis': analysis,
        'created_at': createdAt,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class WritingSession {
  final int? id;
  final String topic;
  final String userWriting;
  final String? feedback;
  final String? grade;
  final String? analysis;
  final String? studyLanguage;
  final String createdAt;
  final String? userNotes;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  WritingSession({
    this.id,
    required this.topic,
    required this.userWriting,
    this.feedback,
    this.grade,
    this.analysis,
    this.studyLanguage,
    required this.createdAt,
    this.userNotes,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory WritingSession.fromJson(Map<String, dynamic> json) {
    return WritingSession(
      id: json['id'],
      topic: json['topic'],
      userWriting: json['user_writing'],
      feedback: json['feedback'],
      grade: json['grade'],
      analysis: json['analysis'],
      studyLanguage: json['study_language'],
      createdAt: json['created_at'],
      userNotes: json['user_notes'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'topic': topic,
        'user_writing': userWriting,
        'feedback': feedback,
        'grade': grade,
        'analysis': analysis,
        'study_language': studyLanguage,
        'created_at': createdAt,
        'user_notes': userNotes,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class Collection {
  final int? id;
  final String name;
  final String type;
  final int? parentId;
  final String createdAt;
  final String? language;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  Collection({
    this.id,
    required this.name,
    required this.type,
    this.parentId,
    required this.createdAt,
    this.language,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory Collection.fromJson(Map<String, dynamic> json) {
    return Collection(
      id: json['id'],
      name: json['name'],
      type: json['type'],
      parentId: json['parent_id'],
      createdAt: json['created_at'],
      language: json['language'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'type': type,
        'parent_id': parentId,
        'created_at': createdAt,
        'language': language,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class RoleplayScenario {
  final int? id;
  final String name;
  final String? description;
  final String userRole;
  final String situation;
  final String characters;
  final String createdAt;
  final String lastUpdated;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  RoleplayScenario({
    this.id,
    required this.name,
    this.description,
    required this.userRole,
    required this.situation,
    required this.characters,
    required this.createdAt,
    required this.lastUpdated,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory RoleplayScenario.fromJson(Map<String, dynamic> json) {
    return RoleplayScenario(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      userRole: json['user_role'],
      situation: json['situation'],
      characters: json['characters'],
      createdAt: json['created_at'],
      lastUpdated: json['last_updated'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'user_role': userRole,
        'situation': situation,
        'characters': characters,
        'created_at': createdAt,
        'last_updated': lastUpdated,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class KnownWord {
  final int? id;
  final String lemma;
  final String language;
  final String? source;
  final String addedAt;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  KnownWord({
    this.id,
    required this.lemma,
    required this.language,
    this.source,
    required this.addedAt,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory KnownWord.fromJson(Map<String, dynamic> json) {
    return KnownWord(
      id: json['id'],
      lemma: json['lemma'],
      language: json['language'],
      source: json['source'],
      addedAt: json['added_at'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'lemma': lemma,
        'language': language,
        'source': source,
        'added_at': addedAt,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ExamAttempt {
  final int? id;
  final String examName;
  final String? level;
  final String? section;
  final int? score;
  final int? totalQuestions;
  final String createdAt;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ExamAttempt({
    this.id,
    required this.examName,
    this.level,
    this.section,
    this.score,
    this.totalQuestions,
    required this.createdAt,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ExamAttempt.fromJson(Map<String, dynamic> json) {
    return ExamAttempt(
      id: json['id'],
      examName: json['exam_name'],
      level: json['level'],
      section: json['section'],
      score: json['score'],
      totalQuestions: json['total_questions'],
      createdAt: json['created_at'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'exam_name': examName,
        'level': level,
        'section': section,
        'score': score,
        'total_questions': totalQuestions,
        'created_at': createdAt,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class ExamQuestion {
  final int? id;
  final int attemptId;
  final String questionText;
  final String correctAnswer;
  final String? choiceA;
  final String? choiceB;
  final String? choiceC;
  final String? choiceD;
  final String? userAnswer;
  final int? isCorrect;
  final String? explanation;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  ExamQuestion({
    this.id,
    required this.attemptId,
    required this.questionText,
    required this.correctAnswer,
    this.choiceA,
    this.choiceB,
    this.choiceC,
    this.choiceD,
    this.userAnswer,
    this.isCorrect,
    this.explanation,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory ExamQuestion.fromJson(Map<String, dynamic> json) {
    return ExamQuestion(
      id: json['id'],
      attemptId: json['attempt_id'],
      questionText: json['question_text'],
      correctAnswer: json['correct_answer'],
      choiceA: json['choice_a'],
      choiceB: json['choice_b'],
      choiceC: json['choice_c'],
      choiceD: json['choice_d'],
      userAnswer: json['user_answer'],
      isCorrect: json['is_correct'],
      explanation: json['explanation'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'attempt_id': attemptId,
        'question_text': questionText,
        'correct_answer': correctAnswer,
        'choice_a': choiceA,
        'choice_b': choiceB,
        'choice_c': choiceC,
        'choice_d': choiceD,
        'user_answer': userAnswer,
        'is_correct': isCorrect,
        'explanation': explanation,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}

class StudySetting {
  final int? id;
  final String settingKey;
  final String settingValue;
  final String? uuid;
  final String? lastModified;
  final String? deletedAt;

  StudySetting({
    this.id,
    required this.settingKey,
    required this.settingValue,
    this.uuid,
    this.lastModified,
    this.deletedAt,
  });

  factory StudySetting.fromJson(Map<String, dynamic> json) {
    return StudySetting(
      id: json['id'],
      settingKey: json['setting_key'],
      settingValue: json['setting_value'],
      uuid: json['uuid'],
      lastModified: json['last_modified'],
      deletedAt: json['deleted_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'setting_key': settingKey,
        'setting_value': settingValue,
        'uuid': uuid,
        'last_modified': lastModified,
        'deleted_at': deletedAt,
      };
}
