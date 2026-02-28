import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import 'import_detail_screen.dart';
import 'word_entry_dialog.dart';

class ImportListScreen extends StatefulWidget {
  final String? contentType; // 'word' or 'sentence'
  
  const ImportListScreen({super.key, this.contentType});

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

    // Build query based on content type filter
    String? whereClause = 'deleted_at IS NULL';
    List<dynamic>? whereArgs;
    
    if (widget.contentType != null) {
      whereClause = 'deleted_at IS NULL AND content_type = ?';
      whereArgs = [widget.contentType];
    }

    final List<Map<String, dynamic>> imports = await db.query(
      'imported_content',
      where: whereClause,
      whereArgs: whereArgs,
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

  Future<void> _showAddWordDialog() async {
    final wordId = await showDialog<int>(
      context: context,
      builder: (context) => WordEntryDialog(
        initialLanguage: 'es', // Could be from user settings
      ),
    );
    
    if (wordId != null) {
      // Reload the list to show the new word
      await _loadImports();
      
      // Navigate to the word detail screen
      if (mounted) {
        final db = await _dbHelper.database;
        final word = await db.query(
          'imported_content',
          where: 'id = ?',
          whereArgs: [wordId],
        );
        
        if (word.isNotEmpty && mounted) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ImportDetailScreen(
                importId: wordId,
                content: word.first['content'] as String? ?? '',
              ),
            ),
          ).then((_) => _loadImports());
        }
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    // Determine title and empty message based on content type
    String title = 'Imported Content';
    String emptyMessage = 'No imported content found.';
    IconData iconData = Icons.extension;
    
    if (widget.contentType == 'word') {
      title = 'Imported Words';
      emptyMessage = 'No imported words found.';
      iconData = Icons.text_fields;
    } else if (widget.contentType == 'sentence') {
      title = 'Imported Sentences';
      emptyMessage = 'No imported sentences found.';
      iconData = Icons.format_quote;
    }
    
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _imports.isEmpty
          ? Center(child: Text(emptyMessage))
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
                    leading: Icon(iconData, color: Colors.orange),
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
      floatingActionButton: widget.contentType == 'word'
          ? FloatingActionButton(
              onPressed: _showAddWordDialog,
              tooltip: 'Add Word',
              child: const Icon(Icons.add),
            )
          : null,
    );
  }
}
