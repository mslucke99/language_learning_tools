import 'dart:convert';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';
import 'package:proficiency_suites/services/llm_service.dart';
import 'package:proficiency_suites/services/prompts.dart';
import 'package:proficiency_suites/services/settings_service.dart';
import 'package:xml/xml.dart' as xml;

class ChatService {
  final DatabaseHelper _db = DatabaseHelper();
  final LLMService _llmService = LLMService();
  final SettingsService? _settings;

  ChatService([this._settings]);
  Future<int> createSession(String topic, String language) async {
    final now = DateTime.now().toIso8601String();

    return await _db.insertItem('chat_sessions', {
      'cur_topic': topic,
      'study_language': language,
      'mode': 'topical',
      'created_at': now,
      'last_updated': now,
    });
  }

  /// Get all chat sessions
  Future<List<ChatSession>> getSessions({String? language}) async {
    final db = await _db.database;

    String query = '''
      SELECT * FROM chat_sessions 
      WHERE deleted_at IS NULL
    ''';

    List<dynamic> args = [];

    if (language != null) {
      query += ' AND study_language = ?';
      args.add(language);
    }

    query += ' ORDER BY last_updated DESC';

    final result = await db.rawQuery(query, args);
    return result.map((json) => ChatSession.fromJson(json)).toList();
  }

  /// Get messages for a session
  Future<List<ChatMessage>> getMessages(int sessionId) async {
    final db = await _db.database;

    final result = await db.query(
      'chat_messages',
      where: 'session_id = ? AND deleted_at IS NULL',
      whereArgs: [sessionId],
      orderBy: 'created_at ASC',
    );

    return result.map((json) => ChatMessage.fromJson(json)).toList();
  }

  /// Send a message and get AI response
  Future<ChatMessage> sendMessage(int sessionId, String content) async {
    // Save user message
    final userMessage = await _saveMessage(sessionId, 'user', content, null);

    // Get session info
    final db = await _db.database;
    final sessionResult = await db.query(
      'chat_sessions',
      where: 'id = ?',
      whereArgs: [sessionId],
    );

    if (sessionResult.isEmpty) {
      throw Exception('Session not found');
    }

    final session = ChatSession.fromJson(sessionResult.first);

    // Get conversation history
    final messages = await getMessages(sessionId);

    // Generate AI response
    final response = await _generateResponse(session, messages, content);

    // Parse response and extract analysis
    final parsedResponse = _parseResponse(response);

    // Save assistant message with analysis
    final assistantMessage = await _saveMessage(
      sessionId,
      'assistant',
      parsedResponse['reply'] ?? response,
      parsedResponse['analysis'],
    );

    // Update session timestamp
    await _db.updateItem('chat_sessions', sessionId, {
      'last_updated': DateTime.now().toIso8601String(),
    });

    return assistantMessage;
  }

  /// Save a message to the database
  Future<ChatMessage> _saveMessage(
    int sessionId,
    String role,
    String content,
    String? analysis,
  ) async {
    final now = DateTime.now().toIso8601String();

    final id = await _db.insertItem('chat_messages', {
      'session_id': sessionId,
      'role': role,
      'content': content,
      'analysis': analysis,
      'created_at': now,
    });

    return ChatMessage(
      id: id,
      sessionId: sessionId,
      role: role,
      content: content,
      analysis: analysis,
      createdAt: now,
    );
  }

  /// Generate AI response using LLM service
  Future<String> _generateResponse(
    ChatSession session,
    List<ChatMessage> history,
    String userMessage,
  ) async {
    // Build system prompt
    final systemPrompt = await _buildSystemPrompt(session);

    // Build conversation context
    final conversationContext = history
        .map(
          (msg) =>
              '${msg.role == 'user' ? 'User' : 'Assistant'}: ${msg.content}',
        )
        .join('\n\n');

    // Build full prompt
    final fullPrompt =
        '''
$systemPrompt

Previous conversation:
$conversationContext

User: $userMessage

Please respond following the XML format specified in the system prompt.
''';

    // Get response from LLM
    return await _llmService.generate(fullPrompt) ??
        'Sorry, no response generated.';
  }

  /// Build system prompt based on session mode
  Future<String> _buildSystemPrompt(ChatSession session) async {
    final mode = session.mode ?? 'topical';
    final topic = session.curTopic ?? 'general conversation';
    final studyLang = session.studyLanguage ?? 'the target language';

    final nativeLang = _settings?.nativeLanguage ?? 'English';

    if (mode == 'roleplay') {
      final template = _settings != null
          ? await Prompts.getTemplate(
              _settings!,
              'chat',
              'system_roleplay',
              'template',
            )
          : '''You are a friendly language tutor roleplaying in {study_language}.
Topic: {topic}
Provide natural responses and helpful feedback.''';

      return template
          .replaceAll('{study_language}', studyLang)
          .replaceAll('{native_language}', nativeLang)
          .replaceAll(
            '{persona}',
            topic,
          ); // Persona is often the topic in roleplay
    } else {
      // Topical mode - we don't have a specific prompt ID for this in prompts.dart yet,
      // but we can use a hardcoded default that respects nativeLang.
      return '''
You are a friendly language tutor helping a student practice $studyLang.

Current topic: $topic

Guidelines:
- Respond naturally in $studyLang
- Correct errors gently
- Provide vocabulary help when needed
- Keep responses conversational
- Adapt to the student's level

After each response, provide analysis in XML format:
<reply>
  (Your natural response in $studyLang)
</reply>
<feedback>
  (Corrections and feedback in $nativeLang)
</feedback>
<vocab>
  (List new words: <flashcard word="TERM" context="SENTENCE">DEFINITION</flashcard>)
</vocab>
<grammar>
  (Explain grammar patterns: <grammar_pattern title="PATTERN">EXPLANATION</grammar_pattern>)
</grammar>
''';
    }
  }

  /// Parse XML response from AI
  Map<String, dynamic> _parseResponse(String response) {
    try {
      // Try to parse as XML
      final document = xml.XmlDocument.parse(response);

      final reply = document.findAllElements('reply').firstOrNull?.text.trim();
      final feedback = document
          .findAllElements('feedback')
          .firstOrNull
          ?.text
          .trim();
      final vocabSection = document
          .findAllElements('vocab')
          .firstOrNull
          ?.text
          .trim();
      final grammarSection = document
          .findAllElements('grammar')
          .firstOrNull
          ?.text
          .trim();

      // Extract flashcards
      final flashcards = <Map<String, String>>[];
      for (final flashcard in document.findAllElements('flashcard')) {
        flashcards.add({
          'word': flashcard.getAttribute('word') ?? '',
          'context': flashcard.getAttribute('context') ?? '',
          'definition': flashcard.text.trim(),
        });
      }

      // Extract grammar patterns
      final grammarPatterns = <Map<String, String>>[];
      for (final pattern in document.findAllElements('grammar_pattern')) {
        grammarPatterns.add({
          'title': pattern.getAttribute('title') ?? '',
          'explanation': pattern.text.trim(),
        });
      }

      // Build analysis JSON
      final analysis = {
        'feedback': feedback,
        'vocab_section': vocabSection,
        'grammar_section': grammarSection,
        'suggestions': {'flashcards': flashcards, 'grammar': grammarPatterns},
      };

      return {'reply': reply ?? response, 'analysis': jsonEncode(analysis)};
    } catch (e) {
      // If parsing fails, return raw response
      return {'reply': response, 'analysis': null};
    }
  }

  /// Get a single chat session by ID
  Future<ChatSession?> getSession(int sessionId) async {
    final db = await _db.database;
    final result = await db.query(
      'chat_sessions',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [sessionId],
      limit: 1,
    );
    if (result.isEmpty) return null;
    return ChatSession.fromJson(result.first);
  }

  /// Delete a chat session
  Future<void> deleteSession(int sessionId) async {
    await _db.softDelete('chat_sessions', sessionId);
  }
}
