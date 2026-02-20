import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class CollectionService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Create a new collection
  Future<int> createCollection({
    required String name,
    required String type,
    int? parentId,
    String? language,
  }) async {
    final now = DateTime.now().toIso8601String();
    
    return await _db.insertItem('collections', {
      'name': name,
      'type': type,
      'parent_id': parentId,
      'language': language,
      'created_at': now,
    });
  }

  /// Get all collections with optional filtering
  Future<List<Collection>> getCollections({
    String? type,
    String? language,
  }) async {
    final db = await _db.database;
    
    String whereClause = 'deleted_at IS NULL';
    List<dynamic> whereArgs = [];
    
    if (type != null) {
      whereClause += ' AND type = ?';
      whereArgs.add(type);
    }
    
    if (language != null) {
      whereClause += ' AND language = ?';
      whereArgs.add(language);
    }
    
    final result = await db.query(
      'collections',
      where: whereClause,
      whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
      orderBy: 'name ASC',
    );

    return result.map((json) => Collection.fromJson(json)).toList();
  }

  /// Get a single collection
  Future<Collection?> getCollection(int collectionId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'collections',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [collectionId],
    );

    if (result.isEmpty) return null;
    return Collection.fromJson(result.first);
  }

  /// Update collection
  Future<void> updateCollection(
    int collectionId, {
    String? name,
    String? type,
    int? parentId,
    String? language,
  }) async {
    final Map<String, dynamic> updates = {};
    
    if (name != null) updates['name'] = name;
    if (type != null) updates['type'] = type;
    if (parentId != null) updates['parent_id'] = parentId;
    if (language != null) updates['language'] = language;
    
    if (updates.isNotEmpty) {
      await _db.updateItem('collections', collectionId, updates);
    }
  }

  /// Delete a collection
  Future<void> deleteCollection(int collectionId) async {
    await _db.softDelete('collections', collectionId);
  }

  /// Get child collections
  Future<List<Collection>> getChildCollections(int parentId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'collections',
      where: 'parent_id = ? AND deleted_at IS NULL',
      whereArgs: [parentId],
      orderBy: 'name ASC',
    );

    return result.map((json) => Collection.fromJson(json)).toList();
  }

  /// Get root collections (no parent)
  Future<List<Collection>> getRootCollections({String? type}) async {
    final db = await _db.database;
    
    String whereClause = 'parent_id IS NULL AND deleted_at IS NULL';
    List<dynamic>? whereArgs;
    
    if (type != null) {
      whereClause += ' AND type = ?';
      whereArgs = [type];
    }
    
    final result = await db.query(
      'collections',
      where: whereClause,
      whereArgs: whereArgs,
      orderBy: 'name ASC',
    );

    return result.map((json) => Collection.fromJson(json)).toList();
  }

  /// Assign item to collection
  Future<void> assignToCollection(
    String itemType,
    int itemId,
    int? collectionId,
  ) async {
    final String table = _getTableForItemType(itemType);
    
    await _db.updateItem(table, itemId, {
      'collection_id': collectionId,
    });
  }

  /// Get items in a collection
  Future<List<Map<String, dynamic>>> getCollectionItems(
    int collectionId,
    String itemType,
  ) async {
    final db = await _db.database;
    final String table = _getTableForItemType(itemType);
    
    final result = await db.query(
      table,
      where: 'collection_id = ? AND deleted_at IS NULL',
      whereArgs: [collectionId],
    );

    return result;
  }

  /// Get item count for a collection
  Future<int> getCollectionItemCount(int collectionId, String itemType) async {
    final db = await _db.database;
    final String table = _getTableForItemType(itemType);
    
    final result = await db.rawQuery(
      'SELECT COUNT(*) as count FROM $table WHERE collection_id = ? AND deleted_at IS NULL',
      [collectionId],
    );

    return result.first['count'] as int;
  }

  /// Helper to map item type to table name
  String _getTableForItemType(String itemType) {
    switch (itemType) {
      case 'deck':
        return 'decks';
      case 'word':
      case 'sentence':
        return 'imported_content';
      case 'grammar':
        return 'grammar_book_entries';
      default:
        throw ArgumentError('Unknown item type: $itemType');
    }
  }
}
