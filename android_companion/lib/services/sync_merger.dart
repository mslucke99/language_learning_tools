import 'dart:async';
import 'package:sqflite/sqflite.dart';

/// Conflict resolution options
enum ConflictResolution {
  keepLocal,
  keepRemote,
  alwaysLocal,
  alwaysRemote,
  cancel,
}

/// Information about a sync conflict
class ConflictInfo {
  final String table;
  final String uuid;
  final String localModified;
  final String remoteModified;
  final Map<String, dynamic> localData;
  final Map<String, dynamic> remoteData;
  final String description;

  ConflictInfo({
    required this.table,
    required this.uuid,
    required this.localModified,
    required this.remoteModified,
    required this.localData,
    required this.remoteData,
    required this.description,
  });
}

/// Callback type for conflict resolution
typedef ConflictCallback =
    Future<ConflictResolution> Function(ConflictInfo conflict);

/// Tables that support sync
const List<String> syncableTables = [
  'decks',
  'flashcards',
  'imported_content',
  'word_definitions',
  'sentence_explanations',
  'writing_sessions',
  'chat_sessions',
  'grammar_book_entries',
  'collections',
];

/// Sync Merger - handles row-by-row comparison between databases
class SyncMerger {
  final Database localDb;
  final Database remoteDb;
  final String lastSyncTime;

  ConflictResolution? _alwaysPreference;
  ConflictCallback? onConflict;

  SyncMerger({
    required this.localDb,
    required this.remoteDb,
    required this.lastSyncTime,
  });

  Future<Map<String, dynamic>> _getAllRows(Database db, String table) async {
    try {
      final List<Map<String, dynamic>> rows = await db.query(
        table,
        where: 'deleted_at IS NULL',
      );
      final Map<String, dynamic> result = {};
      for (final row in rows) {
        if (row['uuid'] != null) {
          result[row['uuid'] as String] = Map<String, dynamic>.from(row);
        }
      }
      return result;
    } catch (e) {
      return {};
    }
  }

  Future<Set<String>> _getDeletedUuids(Database db, String table) async {
    try {
      final List<Map<String, dynamic>> rows = await db.query(
        table,
        columns: ['uuid'],
        where: 'deleted_at IS NOT NULL',
      );
      return rows
          .where((r) => r['uuid'] != null)
          .map((r) => r['uuid'] as String)
          .toSet();
    } catch (e) {
      return {};
    }
  }

  bool _isModifiedSinceSync(String? lastModified) {
    if (lastModified == null || lastModified.isEmpty) return false;
    return lastModified.compareTo(lastSyncTime) > 0;
  }

  Map<String, dynamic> _resolveSrsConflict(
    Map<String, dynamic> local,
    Map<String, dynamic> remote,
  ) {
    final localReviews = (local['total_reviews'] as int?) ?? 0;
    final remoteReviews = (remote['total_reviews'] as int?) ?? 0;
    return localReviews >= remoteReviews ? local : remote;
  }

  String _getItemDescription(String table, Map<String, dynamic> row) {
    switch (table) {
      case 'flashcards':
        return 'Flashcard: ${(row['question'] as String? ?? 'Unknown').substring(0, 50.clamp(0, (row['question'] as String? ?? '').length))}';
      case 'decks':
        return 'Deck: ${row['name'] ?? 'Unknown'}';
      case 'imported_content':
        return 'Import: ${(row['content'] as String? ?? 'Unknown').substring(0, 50.clamp(0, (row['content'] as String? ?? '').length))}';
      case 'word_definitions':
        return 'Word: ${row['word'] ?? 'Unknown'}';
      default:
        return '$table: ${(row['uuid'] as String? ?? 'Unknown').substring(0, 8)}';
    }
  }

  Future<(int, int, int)> mergeTable(String table) async {
    final localRows = await _getAllRows(localDb, table);
    final remoteRows = await _getAllRows(remoteDb, table);
    final localDeleted = await _getDeletedUuids(localDb, table);
    final remoteDeleted = await _getDeletedUuids(remoteDb, table);

    int added = 0;
    int updated = 0;
    int conflicts = 0;

    for (final entry in remoteRows.entries) {
      final uuid = entry.key;
      final remoteRow = entry.value;

      if (localDeleted.contains(uuid)) continue;

      final localRow = localRows[uuid];

      if (localRow == null) {
        // New item from remote
        await _insertRow(table, remoteRow);
        added++;
      } else {
        final localModified = _isModifiedSinceSync(
          localRow['last_modified'] as String?,
        );
        final remoteModified = _isModifiedSinceSync(
          remoteRow['last_modified'] as String?,
        );

        if (localModified && remoteModified) {
          conflicts++;

          // Flashcard SRS: auto-resolve
          if (table == 'flashcards') {
            final winner = _resolveSrsConflict(localRow, remoteRow);
            if (winner == remoteRow) {
              await _updateRow(table, remoteRow);
              updated++;
            }
            continue;
          }

          // Check session preference
          if (_alwaysPreference == ConflictResolution.alwaysLocal) {
            continue;
          } else if (_alwaysPreference == ConflictResolution.alwaysRemote) {
            await _updateRow(table, remoteRow);
            updated++;
            continue;
          }

          // Ask user via callback
          if (onConflict != null) {
            final conflict = ConflictInfo(
              table: table,
              uuid: uuid,
              localModified: localRow['last_modified'] ?? '',
              remoteModified: remoteRow['last_modified'] ?? '',
              localData: localRow,
              remoteData: remoteRow,
              description: _getItemDescription(table, localRow),
            );

            final resolution = await onConflict!(conflict);

            if (resolution == ConflictResolution.cancel) {
              throw Exception('Sync cancelled by user');
            } else if (resolution == ConflictResolution.keepRemote ||
                resolution == ConflictResolution.alwaysRemote) {
              await _updateRow(table, remoteRow);
              updated++;
              if (resolution == ConflictResolution.alwaysRemote) {
                _alwaysPreference = ConflictResolution.alwaysRemote;
              }
            } else if (resolution == ConflictResolution.alwaysLocal) {
              _alwaysPreference = ConflictResolution.alwaysLocal;
            }
          }
        } else if (remoteModified && !localModified) {
          await _updateRow(table, remoteRow);
          updated++;
        }
      }
    }

    // Handle remote deletions
    for (final uuid in remoteDeleted) {
      if (localRows.containsKey(uuid)) {
        final localRow = localRows[uuid]!;
        final localModified = _isModifiedSinceSync(
          localRow['last_modified'] as String?,
        );
        if (!localModified) {
          await _softDeleteRow(table, uuid);
        }
      }
    }

    return (added, updated, conflicts);
  }

  Future<void> _insertRow(String table, Map<String, dynamic> row) async {
    final columns = row.keys.where((k) => k != 'id').toList();
    final values = columns.map((c) => row[c]).toList();
    final placeholders = columns.map((_) => '?').join(', ');
    final colNames = columns.join(', ');
    await localDb.rawInsert(
      'INSERT INTO $table ($colNames) VALUES ($placeholders)',
      values,
    );
  }

  Future<void> _updateRow(String table, Map<String, dynamic> row) async {
    final columns = row.keys.where((k) => k != 'id' && k != 'uuid').toList();
    final setClause = columns.map((c) => '$c = ?').join(', ');
    final values = columns.map((c) => row[c]).toList();
    values.add(row['uuid']);
    await localDb.rawUpdate(
      'UPDATE $table SET $setClause WHERE uuid = ?',
      values,
    );
  }

  Future<void> _softDeleteRow(String table, String uuid) async {
    final now = DateTime.now().toIso8601String();
    await localDb.rawUpdate('UPDATE $table SET deleted_at = ? WHERE uuid = ?', [
      now,
      uuid,
    ]);
  }

  Future<Map<String, (int, int, int)>> mergeAll() async {
    final results = <String, (int, int, int)>{};
    for (final table in syncableTables) {
      try {
        results[table] = await mergeTable(table);
      } catch (e) {
        print('Error merging $table: $e');
        results[table] = (0, 0, 0);
      }
    }
    return results;
  }
}
