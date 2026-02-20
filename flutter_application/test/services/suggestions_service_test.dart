import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:proficiency_suites/models/suggestions.dart';
import 'package:proficiency_suites/services/suggestions_service.dart';
import 'package:proficiency_suites/services/database_helper.dart';

// Simple mock that provides the minimal interface needed
class MockDatabaseHelper implements DatabaseHelper {
  Database? _testDb;
  
  @override
  Future<Database> get database async {
    if (_testDb != null) return _testDb!;
    _testDb = await openDatabase(
      inMemoryDatabasePath,
      version: 1,
      onCreate: (db, version) async {
        await _createTestTables(db);
      },
    );
    return _testDb!;
  }
  
  Future<void> _createTestTables(Database db) async {
    await db.execute('''
      CREATE TABLE sentence_explanations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imported_content_id INTEGER NOT NULL,
        sentence TEXT NOT NULL,
        explanation TEXT NOT NULL,
        grammar_notes TEXT,
        created_at TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        last_modified TEXT
      )
    ''');
    
    await db.execute('''
      CREATE TABLE chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_language TEXT,
        mode TEXT DEFAULT 'topical',
        created_at TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        last_modified TEXT
      )
    ''');
    
    await db.execute('''
      CREATE TABLE chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        analysis TEXT,
        created_at TEXT NOT NULL,
        last_modified TEXT
      )
    ''');
    
    await db.execute('''
      CREATE TABLE writing_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        user_writing TEXT NOT NULL,
        analysis TEXT,
        study_language TEXT,
        created_at TEXT NOT NULL,
        last_modified TEXT
      )
    ''');
  }
  
  @override
  Future<int> insertItem(String table, Map<String, dynamic> data) async {
    final db = await database;
    final Map<String, dynamic> mutableData = Map.from(data);
    mutableData['created_at'] ??= DateTime.now().toIso8601String();
    // Only add last_updated for tables that have it
    if (table == 'sentence_explanations' || table == 'chat_sessions') {
      mutableData['last_updated'] ??= DateTime.now().toIso8601String();
    }
    mutableData['last_modified'] = DateTime.now().toIso8601String();
    return await db.insert(table, mutableData);
  }
  
  @override
  Future<int> updateItem(
    String table,
    int id,
    Map<String, dynamic> data,
  ) async {
    final db = await database;
    final Map<String, dynamic> mutableData = Map.from(data);
    mutableData['last_modified'] = DateTime.now().toIso8601String();
    return await db.update(
      table,
      mutableData,
      where: 'id = ?',
      whereArgs: [id],
    );
  }
  
  // Stub implementations for other DatabaseHelper methods
  @override
  Future<void> initializeSchema() async {}
  
  @override
  Future<String> getDatabasePath() async => inMemoryDatabasePath;
  
  @override
  Future<void> reloadDatabase() async {}
  
  @override
  Future<int> getFlashcardCount() async => 0;
  
  @override
  Future<int> softDelete(String table, int id) async => 0;
  
  @override
  Future<List<Map<String, dynamic>>> getModifiedRowsSince(
    String table,
    String timestamp,
  ) async => [];
  
  @override
  Future<void> upsertRows(String table, List<Map<String, dynamic>> rows) async {}
}

void main() {
  late MockDatabaseHelper dbHelper;
  late SuggestionsService service;
  
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });
  
  setUp(() async {
    dbHelper = MockDatabaseHelper();
    await dbHelper.database;
    service = SuggestionsService(dbHelper);
  });
  
  tearDown(() async {
    final db = await dbHelper.database;
    await db.close();
  });
  
  group('SuggestionsService - Sentence Suggestions', () {
    test('store and retrieve sentence suggestions', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(
            word: 'palabra',
            definition: 'word in Spanish',
          ),
        ],
        grammar: [
          GrammarSuggestion(
            title: 'Present Tense',
            explanation: 'Used for current actions',
          ),
        ],
      );
      
      await service.storeSentenceSuggestions(sentenceId, suggestions);
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      
      expect(retrieved, isNotNull);
      expect(retrieved!.flashcards.length, 1);
      expect(retrieved.flashcards[0].word, 'palabra');
      expect(retrieved.grammar.length, 1);
      expect(retrieved.grammar[0].title, 'Present Tense');
    });
    
    test('return null for non-existent sentence', () async {
      final retrieved = await service.getSentenceSuggestions(99999);
      expect(retrieved, isNull);
    });
    
    test('return null for sentence with no suggestions', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      expect(retrieved, isNull);
    });
    
    test('handle empty suggestions', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final suggestions = Suggestions();
      await service.storeSentenceSuggestions(sentenceId, suggestions);
      
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      expect(retrieved, isNotNull);
      expect(retrieved!.isEmpty, true);
    });
    
    test('update existing suggestions', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final initial = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'old', definition: 'old definition'),
        ],
      );
      await service.storeSentenceSuggestions(sentenceId, initial);
      
      final updated = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'new', definition: 'new definition'),
        ],
      );
      await service.storeSentenceSuggestions(sentenceId, updated);
      
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      expect(retrieved!.flashcards.length, 1);
      expect(retrieved.flashcards[0].word, 'new');
    });
  });
  
  group('SuggestionsService - Chat Suggestions', () {
    test('store and retrieve chat suggestions', () async {
      final sessionId = await dbHelper.insertItem('chat_sessions', {
        'study_language': 'es',
        'mode': 'topical',
      });
      
      final messageId = await dbHelper.insertItem('chat_messages', {
        'session_id': sessionId,
        'role': 'assistant',
        'content': 'Test message',
      });
      
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(
            word: 'hola',
            definition: 'hello',
            context: 'Hola, ¿cómo estás?',
          ),
        ],
      );
      
      await service.storeChatSuggestions(messageId, suggestions);
      final retrieved = await service.getChatSuggestions(messageId);
      
      expect(retrieved, isNotNull);
      expect(retrieved!.flashcards.length, 1);
      expect(retrieved.flashcards[0].word, 'hola');
      expect(retrieved.flashcards[0].context, 'Hola, ¿cómo estás?');
    });
    
    test('return null for non-existent message', () async {
      final retrieved = await service.getChatSuggestions(99999);
      expect(retrieved, isNull);
    });
  });
  
  group('SuggestionsService - Writing Suggestions', () {
    test('store and retrieve writing suggestions', () async {
      final sessionId = await dbHelper.insertItem('writing_sessions', {
        'topic': 'Test topic',
        'user_writing': 'Test writing',
        'study_language': 'es',
      });
      
      final suggestions = Suggestions(
        grammar: [
          GrammarSuggestion(
            title: 'Subjunctive Mood',
            explanation: 'Used for wishes and hypotheticals',
          ),
        ],
      );
      
      await service.storeWritingSuggestions(sessionId, suggestions);
      final retrieved = await service.getWritingSuggestions(sessionId);
      
      expect(retrieved, isNotNull);
      expect(retrieved!.grammar.length, 1);
      expect(retrieved.grammar[0].title, 'Subjunctive Mood');
    });
    
    test('return null for non-existent session', () async {
      final retrieved = await service.getWritingSuggestions(99999);
      expect(retrieved, isNull);
    });
  });
  
  group('SuggestionsService - Error Handling', () {
    test('handle invalid JSON gracefully', () async {
      final db = await dbHelper.database;
      final sentenceId = await db.insert('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
        'grammar_notes': 'invalid json {{{',
        'created_at': DateTime.now().toIso8601String(),
        'last_updated': DateTime.now().toIso8601String(),
      });
      
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      // fromJsonString returns empty Suggestions on parse error, not null
      expect(retrieved, isNotNull);
      expect(retrieved!.isEmpty, true);
    });
  });
  
  group('SuggestionsService - Complex Suggestions', () {
    test('store and retrieve multiple flashcards and grammar patterns', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
          FlashcardSuggestion(word: 'word2', definition: 'def2'),
          FlashcardSuggestion(
            word: 'word3',
            definition: 'def3',
            context: 'context3',
          ),
        ],
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
          GrammarSuggestion(title: 'pattern2', explanation: 'exp2'),
        ],
      );
      
      await service.storeSentenceSuggestions(sentenceId, suggestions);
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      
      expect(retrieved!.flashcards.length, 3);
      expect(retrieved.grammar.length, 2);
      expect(retrieved.totalCount, 5);
    });
    
    test('handle special characters in suggestions', () async {
      final sentenceId = await dbHelper.insertItem('sentence_explanations', {
        'imported_content_id': 1,
        'sentence': 'Test sentence',
        'explanation': 'Test explanation',
      });
      
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(
            word: 'café',
            definition: 'coffee with "quotes" and \'apostrophes\'',
            context: 'Line 1\nLine 2\nLine 3',
          ),
        ],
      );
      
      await service.storeSentenceSuggestions(sentenceId, suggestions);
      final retrieved = await service.getSentenceSuggestions(sentenceId);
      
      expect(retrieved!.flashcards[0].word, 'café');
      expect(retrieved.flashcards[0].definition, contains('quotes'));
      expect(retrieved.flashcards[0].context, contains('\n'));
    });
  });
}
