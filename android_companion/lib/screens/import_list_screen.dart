import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import 'import_detail_screen.dart';

class ImportListScreen extends StatefulWidget {
  const ImportListScreen({super.key});

  @override
  State<ImportListScreen> createState() => _ImportListScreenState();
}

class _ImportListScreenState extends State<ImportListScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _imports = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadImports();
  }

  Future<void> _loadImports() async {
    final db = await _dbHelper.database;
    final tableExists = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='imported_content'",
    )).isNotEmpty;

    if (!tableExists) {
      if (mounted) {
        setState(() {
          _imports = [];
          _isLoading = false;
        });
      }
      return;
    }

    final List<Map<String, dynamic>> imports = await db.query(
      'imported_content',
      where: 'deleted_at IS NULL',
      orderBy: 'created_at DESC',
    );

    if (mounted) {
      setState(() {
        _imports = List.from(imports);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteImport(Map<String, dynamic> item) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Import?'),
        content: const Text(
          'This will remove the item from your list on mobile.',
        ),
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
      await _dbHelper.softDelete('imported_content', item['id']);
      _loadImports();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Imported Content'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _imports.isEmpty
          ? const Center(child: Text('No imported content found.'))
          : ListView.builder(
              itemCount: _imports.length,
              itemBuilder: (context, index) {
                final item = _imports[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.extension, color: Colors.orange),
                    title: Text(
                      item['content'] ?? (item['title'] ?? 'No Content'),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Source: ${item['url'] ?? 'Unknown'}\nDate: ${item['created_at'] != null ? item['created_at'].toString().split('T')[0] : ''}',
                    ),
                    isThreeLine: true,
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      onPressed: () => _deleteImport(item),
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => ImportDetailScreen(
                            importId: item['id'],
                            content: item['content'] ?? (item['title'] ?? ''),
                          ),
                        ),
                      ).then((_) => _loadImports());
                    },
                  ),
                );
              },
            ),
    );
  }
}
