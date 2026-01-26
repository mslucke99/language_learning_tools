import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class FlashcardListScreen extends StatefulWidget {
  final int deckId;
  final String deckName;

  const FlashcardListScreen({
    super.key,
    required this.deckId,
    required this.deckName,
  });

  @override
  State<FlashcardListScreen> createState() => _FlashcardListScreenState();
}

class _FlashcardListScreenState extends State<FlashcardListScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _cards = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCards();
  }

  Future<void> _loadCards() async {
    final db = await _dbHelper.database;
    final List<Map<String, dynamic>> cards = await db.query(
      'flashcards',
      where: 'deck_id = ? AND deleted_at IS NULL',
      whereArgs: [widget.deckId],
    );

    if (mounted) {
      setState(() {
        _cards = List.from(cards);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteCard(int id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Flashcard?'),
        content: const Text(
          'This will mark the card as deleted and sync this change later.',
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
      await _dbHelper.softDelete('flashcards', id);
      _loadCards();
    }
  }

  Future<void> _showCardDialog([Map<String, dynamic>? card]) async {
    final isEditing = card != null;
    final questionController = TextEditingController(
      text: isEditing ? card['question'] : '',
    );
    final answerController = TextEditingController(
      text: isEditing ? card['answer'] : '',
    );

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isEditing ? 'Edit Flashcard' : 'Add Flashcard'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: questionController,
              decoration: const InputDecoration(labelText: 'Question'),
              maxLines: 2,
            ),
            TextField(
              controller: answerController,
              decoration: const InputDecoration(labelText: 'Answer'),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final data = {
                'question': questionController.text,
                'answer': answerController.text,
                'deck_id': widget.deckId,
              };

              if (isEditing) {
                await _dbHelper.updateItem('flashcards', card['id'], data);
              } else {
                await _dbHelper.insertItem('flashcards', data);
              }
              if (mounted) Navigator.pop(context);
              _loadCards();
            },
            child: Text(isEditing ? 'Save' : 'Add'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deckName),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _cards.isEmpty
          ? const Center(child: Text('No cards in this deck.'))
          : ListView.builder(
              itemCount: _cards.length,
              itemBuilder: (context, index) {
                final card = _cards[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  child: ListTile(
                    title: Text(
                      card['question'] ?? 'No Question',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(card['answer'] ?? 'No Answer'),
                    isThreeLine: true,
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.edit_outlined),
                          onPressed: () => _showCardDialog(card),
                        ),
                        IconButton(
                          icon: const Icon(
                            Icons.delete_outline,
                            color: Colors.red,
                          ),
                          onPressed: () => _deleteCard(card['id']),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCardDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
