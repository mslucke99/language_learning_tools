import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class CollectionListScreen extends StatefulWidget {
  const CollectionListScreen({super.key});

  @override
  State<CollectionListScreen> createState() => _CollectionListScreenState();
}

class _CollectionListScreenState extends State<CollectionListScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _collections = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCollections();
  }

  Future<void> _loadCollections() async {
    final db = await _dbHelper.database;
    final tableExists = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='collections'",
    )).isNotEmpty;

    if (!tableExists) {
      if (mounted) {
        setState(() {
          _collections = [];
          _isLoading = false;
        });
      }
      return;
    }

    final List<Map<String, dynamic>> collections = await db.query(
      'collections',
      where: 'deleted_at IS NULL',
    );

    if (mounted) {
      setState(() {
        _collections = List.from(collections);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteCollection(Map<String, dynamic> collection) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete ${collection['name']}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _dbHelper.softDelete('collections', collection['id']);
      _loadCollections();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Collections'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _collections.isEmpty
          ? const Center(child: Text('No collections found.'))
          : ListView.builder(
              itemCount: _collections.length,
              itemBuilder: (context, index) {
                final collection = _collections[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.folder, color: Colors.blue),
                    title: Text(
                      collection['name'] ?? 'Untitled Collection',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text('Type: ${collection['type'] ?? 'General'}'),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      onPressed: () => _deleteCollection(collection),
                    ),
                    onTap: () {
                      // TODO: Implement viewing items within collection if needed
                    },
                  ),
                );
              },
            ),
    );
  }
}
