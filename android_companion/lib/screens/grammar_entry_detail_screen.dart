import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class GrammarEntryDetailScreen extends StatefulWidget {
  final Map<String, dynamic> entry;

  const GrammarEntryDetailScreen({super.key, required this.entry});

  @override
  State<GrammarEntryDetailScreen> createState() =>
      _GrammarEntryDetailScreenState();
}

class _GrammarEntryDetailScreenState extends State<GrammarEntryDetailScreen> {
  late Map<String, dynamic> _entry;
  final DatabaseHelper _dbHelper = DatabaseHelper();

  @override
  void initState() {
    super.initState();
    _entry = Map.from(widget.entry);
  }

  Future<void> _editEntry() async {
    final titleController = TextEditingController(text: _entry['title']);
    final contentController = TextEditingController(text: _entry['content']);

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Grammar Entry'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(labelText: 'Title'),
              ),
              TextField(
                controller: contentController,
                decoration: const InputDecoration(labelText: 'Content'),
                maxLines: 10,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final newTitle = titleController.text;
              final newContent = contentController.text;

              await _dbHelper.updateItem('grammar_book_entries', _entry['id'], {
                'title': newTitle,
                'content': newContent,
              });

              if (mounted) {
                setState(() {
                  _entry['title'] = newTitle;
                  _entry['content'] = newContent;
                });
                Navigator.pop(context);
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_entry['title'] ?? 'Grammar Detail'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            onPressed: _editEntry,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _entry['title'] ?? 'Untitled Entry',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.purple.shade700,
              ),
            ),
            if (_entry['language'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: Chip(
                  label: Text(_entry['language']),
                  backgroundColor: Colors.purple.shade50,
                ),
              ),
            const Divider(height: 32),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.grey.withOpacity(0.1),
                    spreadRadius: 2,
                    blurRadius: 5,
                  ),
                ],
              ),
              child: Text(
                _entry['content'] ?? 'No content available.',
                style: const TextStyle(fontSize: 16, height: 1.6),
              ),
            ),
            if (_entry['tags'] != null &&
                _entry['tags'].toString().isNotEmpty) ...[
              const SizedBox(height: 24),
              const Text(
                'Tags:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: _entry['tags']
                    .toString()
                    .split(',')
                    .map(
                      (tag) => Chip(
                        label: Text(tag.trim()),
                        visualDensity: VisualDensity.compact,
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
