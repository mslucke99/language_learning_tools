import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/known_words_service.dart';

class KnownWordsScreen extends StatefulWidget {
  final String language;

  const KnownWordsScreen({
    super.key,
    required this.language,
  });

  @override
  State<KnownWordsScreen> createState() => _KnownWordsScreenState();
}

class _KnownWordsScreenState extends State<KnownWordsScreen> {
  final KnownWordsService _knownWordsService = KnownWordsService();
  final TextEditingController _searchController = TextEditingController();
  
  List<KnownWord> _words = [];
  int _wordCount = 0;
  bool _isLoading = true;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadWords();
  }

  Future<void> _loadWords() async {
    setState(() => _isLoading = true);
    
    try {
      final count = await _knownWordsService.getKnownWordCount(widget.language);
      final words = _searchQuery.isEmpty
          ? await _knownWordsService.getKnownWords(widget.language)
          : await _knownWordsService.searchKnownWords(_searchQuery, widget.language);

      setState(() {
        _wordCount = count;
        _words = words;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  Future<void> _addWord() async {
    final controller = TextEditingController();
    
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Known Word'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Word',
            hintText: 'Enter a word',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Add'),
          ),
        ],
      ),
    );

    if (result != null && result.isNotEmpty) {
      await _knownWordsService.addWord(result, widget.language);
      _loadWords();
    }
  }

  Future<void> _bulkImport() async {
    final controller = TextEditingController();
    
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Bulk Import Words'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Paste text containing words to import:'),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Paste text here...',
              ),
              maxLines: 10,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Import'),
          ),
        ],
      ),
    );

    if (result != null && result.isNotEmpty) {
      final count = await _knownWordsService.importFromText(result, widget.language);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Imported $count words')),
        );
      }
      _loadWords();
    }
  }

  Future<void> _syncFromFlashcards() async {
    final count = await _knownWordsService.syncFromFlashcards(widget.language);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Added $count words from flashcards')),
      );
    }
    _loadWords();
  }

  Future<void> _deleteWord(KnownWord word) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Word'),
        content: Text('Remove "${word.lemma}" from known words?'),
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
      await _knownWordsService.removeWord(word.id!);
      _loadWords();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Known Words ($_wordCount)'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'sync') {
                _syncFromFlashcards();
              } else if (value == 'bulk') {
                _bulkImport();
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'sync',
                child: Row(
                  children: [
                    Icon(Icons.sync),
                    SizedBox(width: 8),
                    Text('Sync from Flashcards'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'bulk',
                child: Row(
                  children: [
                    Icon(Icons.upload),
                    SizedBox(width: 8),
                    Text('Bulk Import'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                labelText: 'Search words',
                prefixIcon: const Icon(Icons.search),
                border: const OutlineInputBorder(),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                          _loadWords();
                        },
                      )
                    : null,
              ),
              onChanged: (value) {
                setState(() => _searchQuery = value);
                _loadWords();
              },
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _words.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.library_books, size: 64, color: Colors.grey),
                            const SizedBox(height: 16),
                            Text(
                              _searchQuery.isEmpty
                                  ? 'No known words yet'
                                  : 'No words found',
                            ),
                            const SizedBox(height: 8),
                            if (_searchQuery.isEmpty)
                              const Text(
                                'Add words manually or sync from flashcards',
                                style: TextStyle(color: Colors.grey),
                              ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _words.length,
                        itemBuilder: (context, index) {
                          final word = _words[index];
                          return ListTile(
                            leading: CircleAvatar(
                              backgroundColor: _getSourceColor(word.source),
                              child: Text(
                                word.lemma[0].toUpperCase(),
                                style: const TextStyle(color: Colors.white),
                              ),
                            ),
                            title: Text(word.lemma),
                            subtitle: Text(_getSourceLabel(word.source)),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete, color: Colors.red),
                              onPressed: () => _deleteWord(word),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addWord,
        child: const Icon(Icons.add),
      ),
    );
  }

  Color _getSourceColor(String? source) {
    switch (source) {
      case 'flashcard':
        return Colors.teal;
      case 'frequency':
        return Colors.blue;
      case 'mining':
        return Colors.orange;
      case 'import':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  String _getSourceLabel(String? source) {
    switch (source) {
      case 'flashcard':
        return 'From flashcards';
      case 'frequency':
        return 'Frequency list';
      case 'mining':
        return 'Sentence mining';
      case 'import':
        return 'Bulk import';
      default:
        return 'Manual';
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }
}
