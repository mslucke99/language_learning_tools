import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class ImportDetailScreen extends StatefulWidget {
  final int importId;
  final String content;

  const ImportDetailScreen({
    super.key,
    required this.importId,
    required this.content,
  });

  @override
  State<ImportDetailScreen> createState() => _ImportDetailScreenState();
}

class _ImportDetailScreenState extends State<ImportDetailScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _definitions = [];
  List<Map<String, dynamic>> _explanations = [];
  List<Map<String, dynamic>> _decks = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRelatedItems();
  }

  Future<void> _loadRelatedItems() async {
    final db = await _dbHelper.database;

    // Load definitions
    final defs = await db.query(
      'word_definitions',
      where: 'imported_content_id = ? AND deleted_at IS NULL',
      whereArgs: [widget.importId],
    );

    // Load explanations
    final expls = await db.query(
      'sentence_explanations',
      where: 'imported_content_id = ? AND deleted_at IS NULL',
      whereArgs: [widget.importId],
    );

    // Load decks for "Add to Deck"
    final decks = await db.query(
      'decks',
      where: 'deleted_at IS NULL',
      orderBy: 'name ASC',
    );

    if (mounted) {
      setState(() {
        _definitions = defs;
        _explanations = expls;
        _decks = decks;
        _isLoading = false;
      });
    }
  }

  Future<void> _addToDeck(Map<String, dynamic> item, bool isDefinition) async {
    if (_decks.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No decks found. Create one first!')),
      );
      return;
    }

    final selectedDeck = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Deck'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: _decks.length,
            itemBuilder: (context, index) {
              final deck = _decks[index];
              return ListTile(
                title: Text(deck['name'] ?? 'Unnamed Deck'),
                subtitle: Text(deck['language'] ?? ''),
                onTap: () => Navigator.pop(context, deck),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );

    if (selectedDeck != null) {
      final deckId = selectedDeck['id'] as int;
      final String question;
      final String answer;

      if (isDefinition) {
        question = item['word'] ?? '';
        answer = item['definition'] ?? '';
      } else {
        question = item['sentence'] ?? '';
        answer = item['explanation'] ?? '';
      }

      await _dbHelper.insertItem('flashcards', {
        'deck_id': deckId,
        'question': question,
        'answer': answer,
        'user_notes': item['notes'] ?? item['grammar_notes'] ?? '',
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Added to ${selectedDeck['name']}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Import Detail'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Original Content',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.teal,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey.shade300),
                    ),
                    child: Text(
                      widget.content,
                      style: const TextStyle(fontSize: 16),
                    ),
                  ),
                  const SizedBox(height: 24),
                  if (_definitions.isNotEmpty) ...[
                    const Text(
                      'Word Definitions',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._definitions.map((def) => _buildDefinitionCard(def)),
                    const SizedBox(height: 16),
                  ],
                  if (_explanations.isNotEmpty) ...[
                    const Text(
                      'Sentence Explanations',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._explanations.map((expl) => _buildExplanationCard(expl)),
                  ],
                  if (_definitions.isEmpty && _explanations.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 32.0),
                      child: Center(
                        child: Text(
                          'No related items found. Try generating analysis on PC!',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.grey,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _buildDefinitionCard(Map<String, dynamic> def) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  def['word'] ?? '',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                IconButton(
                  icon: const Icon(
                    Icons.add_circle_outline,
                    color: Colors.teal,
                  ),
                  onPressed: () => _addToDeck(def, true),
                ),
              ],
            ),
            const Divider(),
            Text(def['definition'] ?? '', style: const TextStyle(fontSize: 16)),
            if (def['examples'] != null &&
                def['examples'].toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'Examples:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(def['examples']),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildExplanationCard(Map<String, dynamic> expl) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Icon(Icons.psychology, color: Colors.blue),
                IconButton(
                  icon: const Icon(
                    Icons.add_circle_outline,
                    color: Colors.teal,
                  ),
                  onPressed: () => _addToDeck(expl, false),
                ),
              ],
            ),
            Text(
              expl['sentence'] ?? '',
              style: const TextStyle(fontSize: 16, fontStyle: FontStyle.italic),
            ),
            const Divider(),
            Text(
              expl['explanation'] ?? '',
              style: const TextStyle(fontSize: 16),
            ),
            if (expl['grammar_notes'] != null &&
                expl['grammar_notes'].toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'Grammar Notes:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(expl['grammar_notes']),
            ],
          ],
        ),
      ),
    );
  }
}
