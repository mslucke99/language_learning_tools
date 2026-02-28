import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:proficiency_suites/screens/word_entry_dialog.dart';
import 'package:proficiency_suites/services/database_helper.dart';

// Mock database helper for testing
class MockDatabaseHelper implements DatabaseHelper {
  Database? _testDb;
  
  @override
  Future<Database> get database async {
    if (_testDb != null) return _testDb!;
    _testDb = await openDatabase(
      inMemoryDatabasePath,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE imported_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            context TEXT,
            url TEXT NOT NULL,
            language TEXT,
            created_at TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            last_modified TEXT
          )
        ''');
      },
    );
    return _testDb!;
  }
  
  @override
  Future<int> insertItem(String table, Map<String, dynamic> data) async {
    final db = await database;
    final Map<String, dynamic> mutableData = Map.from(data);
    mutableData['created_at'] ??= DateTime.now().toIso8601String();
    mutableData['last_modified'] = DateTime.now().toIso8601String();
    return await db.insert(table, mutableData);
  }
  
  // Stub implementations
  @override
  Future<void> initializeSchema() async {}
  
  @override
  Future<String> getDatabasePath() async => inMemoryDatabasePath;
  
  @override
  Future<void> reloadDatabase() async {}
  
  @override
  Future<int> getFlashcardCount() async => 0;
  
  @override
  Future<int> updateItem(String table, int id, Map<String, dynamic> data) async => 0;
  
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
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });
  
  group('WordEntryDialog Widget Tests', () {
    testWidgets('dialog displays all fields', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      expect(find.text('Add Word'), findsOneWidget);
      expect(find.text('Word *'), findsOneWidget);
      expect(find.text('Context (optional)'), findsOneWidget);
      expect(find.text('Source URL (optional)'), findsOneWidget);
      expect(find.text('Language'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Save'), findsOneWidget);
    });
    
    testWidgets('word field validation shows error when empty', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      // Tap save without entering a word
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      
      expect(find.text('Word is required'), findsOneWidget);
    });
    
    testWidgets('cancel button closes dialog', (WidgetTester tester) async {
      bool dialogClosed = false;
      
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  final result = await showDialog(
                    context: context,
                    builder: (context) => const WordEntryDialog(),
                  );
                  if (result == null) {
                    dialogClosed = true;
                  }
                },
                child: const Text('Show Dialog'),
              ),
            ),
          ),
        ),
      );
      
      await tester.tap(find.text('Show Dialog'));
      await tester.pumpAndSettle();
      
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      
      expect(dialogClosed, true);
    });
    
    testWidgets('language dropdown shows options', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      // Find and tap the language dropdown
      await tester.tap(find.text('Spanish'));
      await tester.pumpAndSettle();
      
      // Verify language options are shown
      expect(find.text('French'), findsOneWidget);
      expect(find.text('German'), findsOneWidget);
      expect(find.text('Italian'), findsOneWidget);
    });
    
    testWidgets('word field accepts input', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      // Enter text in word field
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Word *'),
        'palabra',
      );
      await tester.pump();
      
      expect(find.text('palabra'), findsOneWidget);
    });
    
    testWidgets('context field accepts input', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      // Enter text in context field
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Context (optional)'),
        'from news article',
      );
      await tester.pump();
      
      expect(find.text('from news article'), findsOneWidget);
    });
    
    testWidgets('initial language is set correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(initialLanguage: 'fr'),
          ),
        ),
      );
      
      expect(find.text('French'), findsOneWidget);
    });
    
    testWidgets('save button shows loading indicator when saving', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      // Enter a valid word
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Word *'),
        'test',
      );
      await tester.pump();
      
      // Tap save
      await tester.tap(find.text('Save'));
      await tester.pump();
      
      // Should show loading indicator briefly
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
  
  group('WordEntryDialog Validation Tests', () {
    testWidgets('empty word shows validation error', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      
      expect(find.text('Word is required'), findsOneWidget);
    });
    
    testWidgets('whitespace-only word shows validation error', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Word *'),
        '   ',
      );
      await tester.pump();
      
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      
      expect(find.text('Word is required'), findsOneWidget);
    });
    
    testWidgets('valid word passes validation', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WordEntryDialog(),
          ),
        ),
      );
      
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Word *'),
        'palabra',
      );
      await tester.pump();
      
      await tester.tap(find.text('Save'));
      await tester.pump();
      
      // Should not show validation error
      expect(find.text('Word is required'), findsNothing);
    });
  });
}
