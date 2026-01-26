import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import 'flashcard_list_screen.dart';

class DeckListScreen extends StatefulWidget {
  const DeckListScreen({super.key});

  @override
  State<DeckListScreen> createState() => _DeckListScreenState();
}

class _DeckListScreenState extends State<DeckListScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _decks = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDecks();
  }

  Future<void> _loadDecks() async {
    final db = await _dbHelper.database;
    // We check if the table exists first because of our new robustness strategy
    final tableExists = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='decks'",
    )).isNotEmpty;

    if (!tableExists) {
      if (mounted) {
        setState(() {
          _decks = [];
          _isLoading = false;
        });
      }
      return;
    }

    final List<Map<String, dynamic>> decks = await db.query(
      'decks',
      where: 'deleted_at IS NULL',
    );

    // For each deck, count flashcards
    List<Map<String, dynamic>> decksWithCounts = [];
    for (var deck in decks) {
      final countResult = await db.rawQuery(
        'SELECT COUNT(*) as count FROM flashcards WHERE deck_id = ? AND deleted_at IS NULL',
        [deck['id']],
      );
      final count = countResult.first['count'] as int;

      var deckMap = Map<String, dynamic>.from(deck);
      deckMap['cardCount'] = count;
      decksWithCounts.add(deckMap);
    }

    if (mounted) {
      setState(() {
        _decks = List.from(decksWithCounts);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteDeck(Map<String, dynamic> deck) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete ${deck['name']}?'),
        content: const Text(
          'This will hide the deck and all its cards. You can still access them on PC.',
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
      await _dbHelper.softDelete('decks', deck['id']);
      _loadDecks();
    }
  }

  Future<void> _showDeckDialog([Map<String, dynamic>? deck]) async {
    final isEditing = deck != null;
    final nameController = TextEditingController(
      text: isEditing ? deck['name'] : '',
    );
    final langController = TextEditingController(
      text: isEditing ? deck['language'] : '',
    );
    final descController = TextEditingController(
      text: isEditing ? deck['description'] : '',
    );

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isEditing ? 'Edit Deck' : 'Create Deck'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Deck Name'),
              ),
              TextField(
                controller: langController,
                decoration: const InputDecoration(
                  labelText: 'Language (e.g. Spanish)',
                ),
              ),
              TextField(
                controller: descController,
                decoration: const InputDecoration(
                  labelText: 'Description (Optional)',
                ),
                maxLines: 2,
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
              if (nameController.text.isEmpty) return;

              final data = {
                'name': nameController.text,
                'language': langController.text,
                'description': descController.text,
              };

              if (isEditing) {
                await _dbHelper.updateItem('decks', deck['id'], data);
              } else {
                await _dbHelper.insertItem('decks', data);
              }
              if (mounted) Navigator.pop(context);
              _loadDecks();
            },
            child: Text(isEditing ? 'Save' : 'Create'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Decks'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _loadDecks();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _decks.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.folder_open, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No decks found. Sync to get started!'),
                ],
              ),
            )
          : ListView.builder(
              itemCount: _decks.length,
              itemBuilder: (context, index) {
                final deck = _decks[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.style, color: Colors.teal),
                    title: Text(
                      deck['name'] ?? 'Untitled Deck',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      '${deck['cardCount']} cards • ${deck['language'] ?? 'No language'}',
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (value) {
                        if (value == 'edit') {
                          _showDeckDialog(deck);
                        } else if (value == 'delete') {
                          _deleteDeck(deck);
                        }
                      },
                      itemBuilder: (context) => [
                        const PopupMenuItem(value: 'edit', child: Text('Edit')),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Text(
                            'Delete',
                            style: TextStyle(color: Colors.red),
                          ),
                        ),
                      ],
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => FlashcardListScreen(
                            deckId: deck['id'],
                            deckName: deck['name'] ?? 'Unknown Deck',
                          ),
                        ),
                      ).then((_) => _loadDecks()); // Reload on return
                    },
                  ),
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showDeckDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
