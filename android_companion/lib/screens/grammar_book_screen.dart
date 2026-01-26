import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import 'grammar_entry_detail_screen.dart';

class GrammarBookScreen extends StatefulWidget {
  const GrammarBookScreen({super.key});

  @override
  State<GrammarBookScreen> createState() => _GrammarBookScreenState();
}

class _GrammarBookScreenState extends State<GrammarBookScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _entries = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadEntries();
  }

  Future<void> _loadEntries() async {
    final db = await _dbHelper.database;
    final tableExists = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='grammar_book_entries'",
    )).isNotEmpty;

    if (!tableExists) {
      if (mounted) {
        setState(() {
          _entries = [];
          _isLoading = false;
        });
      }
      return;
    }

    final List<Map<String, dynamic>> entries = await db.query(
      'grammar_book_entries',
      where: 'deleted_at IS NULL',
      orderBy: 'title ASC',
    );

    if (mounted) {
      setState(() {
        _entries = List.from(entries);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteEntry(Map<String, dynamic> entry) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete ${entry['title']}?'),
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
      await _dbHelper.softDelete('grammar_book_entries', entry['id']);
      _loadEntries();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Grammar Book'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _entries.isEmpty
          ? const Center(child: Text('No grammar entries found.'))
          : ListView.builder(
              itemCount: _entries.length,
              itemBuilder: (context, index) {
                final entry = _entries[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  child: ListTile(
                    leading: const Icon(
                      Icons.history_edu,
                      color: Colors.purple,
                    ),
                    title: Text(
                      entry['title'] ?? 'Untitled Entry',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      (entry['content'] ?? '').toString().substring(
                            0,
                            (entry['content'] ?? '').toString().length.clamp(
                              0,
                              100,
                            ),
                          ) +
                          '...',
                      maxLines: 2,
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      onPressed: () => _deleteEntry(entry),
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) =>
                              GrammarEntryDetailScreen(entry: entry),
                        ),
                      ).then((_) => _loadEntries());
                    },
                  ),
                );
              },
            ),
    );
  }
}
