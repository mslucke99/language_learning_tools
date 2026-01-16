import 'dart:io';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  static Database? _database;

  factory DatabaseHelper() {
    return _instance;
  }

  DatabaseHelper._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<void> initializeSchema() async {
    final db = await database;
    await _createTables(db);
  }

  Future<String> getDatabasePath() async {
    final documentsDirectory = await getApplicationDocumentsDirectory();
    return join(documentsDirectory.path, 'flashcards.db');
  }

  Future<Database> _initDatabase() async {
    final path = await getDatabasePath();

    // Check if DB exists
    final exists = await File(path).exists();
    if (!exists) {
      print("Database does not exist at $path. Waiting for sync.");
      // We can return a generic empty DB or handle this gracefully.
      // For now, let's open it (it will be created empty if not exists,
      // but we expect it to be overwritten by Drive sync).
    }

    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await _createTables(db);
      },
      onOpen: (db) {
        print("Database opened from $path");
      },
    );
  }

  Future<void> _createTables(Database db) async {
    print("Initializing syncable tables...");

    await db.execute('''
      CREATE TABLE IF NOT EXISTS decks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        description TEXT,
        language TEXT,
        collection_id INTEGER,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deck_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        last_reviewed TEXT,
        easiness REAL DEFAULT 2.5,
        interval INTEGER DEFAULT 1,
        repetitions INTEGER DEFAULT 0,
        total_reviews INTEGER DEFAULT 0,
        correct_reviews INTEGER DEFAULT 0,
        user_notes TEXT,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS imported_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_type TEXT NOT NULL,
        content TEXT NOT NULL,
        context TEXT,
        title TEXT,
        url TEXT NOT NULL,
        language TEXT,
        created_at TEXT NOT NULL,
        processed INTEGER DEFAULT 0,
        tags TEXT,
        collection_id INTEGER,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS word_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imported_content_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        definition TEXT NOT NULL,
        definition_language TEXT,
        source TEXT DEFAULT 'user',
        created_at TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        examples TEXT,
        notes TEXT,
        difficulty_level INTEGER DEFAULT 0,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS sentence_explanations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imported_content_id INTEGER NOT NULL,
        sentence TEXT NOT NULL,
        explanation TEXT NOT NULL,
        explanation_language TEXT,
        source TEXT DEFAULT 'user',
        focus_area TEXT,
        created_at TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        grammar_notes TEXT,
        user_notes TEXT,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS writing_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        user_writing TEXT NOT NULL,
        feedback TEXT,
        grade TEXT,
        analysis TEXT,
        study_language TEXT,
        created_at TEXT NOT NULL,
        user_notes TEXT,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cur_topic TEXT,
        study_language TEXT,
        created_at TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        user_notes TEXT,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS grammar_book_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        language TEXT,
        tags TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        collection_id INTEGER,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        parent_id INTEGER,
        created_at TEXT NOT NULL,
        language TEXT,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        analysis TEXT,
        created_at TEXT NOT NULL,
        uuid TEXT UNIQUE,
        last_modified TEXT,
        deleted_at TEXT,
        FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
      )
    ''');
  }

  // Reload DB connection (useful after overwriting the file)
  Future<void> reloadDatabase() async {
    if (_database != null) {
      await _database!.close();
      _database = null;
    }
    _database = await _initDatabase();
  }

  Future<int> getFlashcardCount() async {
    try {
      final db = await database;
      // SQLite count query
      final result = await db.rawQuery(
        'SELECT COUNT(*) as count FROM flashcards',
      );
      if (result.isNotEmpty) {
        return result.first['count'] as int;
      }
      return 0;
    } catch (e) {
      print("Error counting flashcards: $e");
      return -1;
    }
  }

  // ===== CRUD UTILITIES =====

  Future<int> insertItem(String table, Map<String, dynamic> data) async {
    final db = await database;
    final Map<String, dynamic> mutableData = Map.from(data);

    // Add sync metadata
    mutableData['uuid'] ??= const Uuid().v4();
    mutableData['last_modified'] = DateTime.now().toIso8601String();
    mutableData['created_at'] ??= DateTime.now().toIso8601String();

    return await db.insert(table, mutableData);
  }

  Future<int> updateItem(
    String table,
    int id,
    Map<String, dynamic> data,
  ) async {
    final db = await database;
    final Map<String, dynamic> mutableData = Map.from(data);

    // Update sync metadata
    mutableData['last_modified'] = DateTime.now().toIso8601String();

    return await db.update(
      table,
      mutableData,
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> softDelete(String table, int id) async {
    final db = await database;
    final now = DateTime.now().toIso8601String();

    return await db.update(
      table,
      {'deleted_at': now, 'last_modified': now},
      where: 'id = ?',
      whereArgs: [id],
    );
  }
}
