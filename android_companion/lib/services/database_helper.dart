import 'dart:io';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

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

  Future<Database> _initDatabase() async {
    final documentsDirectory = await getApplicationDocumentsDirectory();
    final path = join(documentsDirectory.path, 'flashcards.db');

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
      onCreate: (db, version) {
        // If we are creating it fresh on mobile (not synced yet),
        // we might want to create tables. But really we rely on Sync.
        // For now, empty is fine.
      },
      onOpen: (db) {
        print("Database opened from $path");
      },
    );
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
}
