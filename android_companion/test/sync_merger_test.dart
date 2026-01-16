import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:android_companion/services/sync_merger.dart';
import 'dart:io';
import 'package:path/path.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  Future<Database> createTestDb(String path) async {
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
        CREATE TABLE flashcards (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE,
            question TEXT,
            answer TEXT,
            last_modified TEXT,
            deleted_at TEXT,
            total_reviews INTEGER DEFAULT 0
        )
      ''');
      },
    );
  }

  Future<void> insertCard(
    Database db,
    String uuid,
    String question,
    String lastModified, {
    int totalReviews = 0,
    String? deletedAt,
  }) async {
    await db.insert('flashcards', {
      'uuid': uuid,
      'question': question,
      'answer': 'A',
      'last_modified': lastModified,
      'total_reviews': totalReviews,
      'deleted_at': deletedAt,
    });
  }

  Future<Map<String, dynamic>?> getCard(Database db, String uuid) async {
    final res = await db.query(
      'flashcards',
      where: 'uuid = ?',
      whereArgs: [uuid],
    );
    return res.isNotEmpty ? res.first : null;
  }

  test('New item from remote should be added', () async {
    final tempDir = await Directory.systemTemp.createTemp();
    final localPath = join(tempDir.path, 'local.db');
    final remotePath = join(tempDir.path, 'remote.db');

    final localDb = await createTestDb(localPath);
    final remoteDb = await createTestDb(remotePath);

    final uuid = '123';
    final now = DateTime.now().toIso8601String();

    await insertCard(remoteDb, uuid, 'Hola', now);

    final merger = SyncMerger(
      localDb: localDb,
      remoteDb: remoteDb,
      lastSyncTime: '1970-01-01',
    );

    final (added, updated, conflicts) = await merger.mergeTable('flashcards');

    expect(added, 1);
    expect(updated, 0);
    expect(conflicts, 0);

    final card = await getCard(localDb, uuid);
    expect(card, isNotNull);
    expect(card!['question'], 'Hola');

    await localDb.close();
    await remoteDb.close();
    await tempDir.delete(recursive: true);
  });

  test('SRS Conflict: Remote wins (more reviews)', () async {
    final tempDir = await Directory.systemTemp.createTemp();
    final localPath = join(tempDir.path, 'local_srs.db');
    final remotePath = join(tempDir.path, 'remote_srs.db');

    final localDb = await createTestDb(localPath);
    final remoteDb = await createTestDb(remotePath);

    final uuid = '123';
    final now = DateTime.now().toIso8601String();

    await insertCard(localDb, uuid, 'Q', now, totalReviews: 5);
    await insertCard(remoteDb, uuid, 'Q', now, totalReviews: 10);

    final merger = SyncMerger(
      localDb: localDb,
      remoteDb: remoteDb,
      lastSyncTime: '1970-01-01',
    );

    final (_, updated, conflicts) = await merger.mergeTable('flashcards');

    expect(conflicts, 1);
    expect(updated, 1); // Remote updated local

    final card = await getCard(localDb, uuid);
    expect(card!['total_reviews'], 10);

    await localDb.close();
    await remoteDb.close();
    await tempDir.delete(recursive: true);
  });

  test('SRS Conflict: Local wins (more reviews)', () async {
    final tempDir = await Directory.systemTemp.createTemp();
    final localPath = join(tempDir.path, 'local_srs2.db');
    final remotePath = join(tempDir.path, 'remote_srs2.db');

    final localDb = await createTestDb(localPath);
    final remoteDb = await createTestDb(remotePath);

    final uuid = '123';
    final now = DateTime.now().toIso8601String();

    await insertCard(localDb, uuid, 'Q', now, totalReviews: 20);
    await insertCard(remoteDb, uuid, 'Q', now, totalReviews: 10);

    final merger = SyncMerger(
      localDb: localDb,
      remoteDb: remoteDb,
      lastSyncTime: '1970-01-01',
    );

    final (_, updated, conflicts) = await merger.mergeTable('flashcards');

    expect(conflicts, 1);
    expect(updated, 0); // Local kept

    final card = await getCard(localDb, uuid);
    expect(card!['total_reviews'], 20);

    await localDb.close();
    await remoteDb.close();
    await tempDir.delete(recursive: true);
  });
}
