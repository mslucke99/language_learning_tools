import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import '../services/database_helper.dart';
import '../services/llm_service.dart';
import '../services/prompts.dart';
import '../services/word_content_service.dart';
import '../models/word_definition.dart';
import 'package:uuid/uuid.dart';

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
  Map<String, dynamic>? _importedContent;
  bool _isLoading = true;
  bool _isGeneratingDefinition = false;
  bool _isGeneratingExamples = false;

  @override
  void initState() {
    super.initState();
    _loadRelatedItems();
  }

  Future<void> _loadRelatedItems() async {
    final db = await _dbHelper.database;

    // Load imported content details
    final content = await db.query(
      'imported_content',
      where: 'id = ?',
      whereArgs: [widget.importId],
    );
    
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
        _importedContent = content.isNotEmpty ? content.first : null;
        _definitions = defs;
        _explanations = expls;
        _decks = decks;
        _isLoading = false;
      });
    }
  }
  
  Future<void> _generateDefinition(bool useNativeLanguage) async {
    if (_importedContent == null) return;
    
    setState(() {
      _isGeneratingDefinition = true;
    });
    
    try {
      final llmService = Provider.of<LLMService>(context, listen: false);
      final wordContentService = WordContentService(_dbHelper, llmService);
      
      final language = _importedContent!['language'] as String? ?? 'es';
      
      await wordContentService.generateDefinition(
        importedContentId: widget.importId,
        word: widget.content,
        language: language,
        useNativeLanguage: useNativeLanguage,
      );
      
      await _loadRelatedItems();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Definition generated successfully!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error generating definition: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isGeneratingDefinition = false;
        });
      }
    }
  }
  
  Future<void> _showGenerateDefinitionDialog() async {
    final choice = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Generate Definition'),
        content: const Text('Choose definition language:'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Study Language'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Native Language'),
          ),
        ],
      ),
    );
    
    if (choice != null) {
      await _generateDefinition(choice);
    }
  }
  
  Future<void> _updateDifficulty(int definitionId, int difficulty) async {
    try {
      final llmService = Provider.of<LLMService>(context, listen: false);
      final wordContentService = WordContentService(_dbHelper, llmService);
      
      await wordContentService.updateDifficulty(definitionId, difficulty);
      await _loadRelatedItems();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error updating difficulty: $e')),
        );
      }
    }
  }
  
  Future<void> _generateExamples(int definitionId) async {
    if (_importedContent == null) return;
    
    setState(() {
      _isGeneratingExamples = true;
    });
    
    try {
      final llmService = Provider.of<LLMService>(context, listen: false);
      final wordContentService = WordContentService(_dbHelper, llmService);
      
      final language = _importedContent!['language'] as String? ?? 'es';
      
      await wordContentService.generateExamples(
        wordDefinitionId: definitionId,
        word: widget.content,
        studyLanguage: language,
        nativeLanguage: 'en', // TODO: Get from settings
        count: 3,
      );
      
      await _loadRelatedItems();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Examples generated successfully!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error generating examples: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isGeneratingExamples = false;
        });
      }
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

  String _selectedText = '';

  Future<void> _explainSelection() async {
    if (_selectedText.isEmpty) return;

    // Show loading dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final llmService = Provider.of<LLMService>(context, listen: false);
      final prompt = Prompts.format(
        Prompts.sentencePrompts['all']!['template']!,
        {
          'sentence': _selectedText,
          'language': 'English', // TODO
        },
      );
      final result = await llmService.generate(prompt);

      if (mounted) Navigator.pop(context); // Close loading

      if (result != null) {
        // Save to DB
        final expl = {
          'imported_content_id': widget.importId,
          'sentence': _selectedText,
          'explanation': result,
          'created_at': DateTime.now().toIso8601String(),
          'uuid': const Uuid().v4(),
        };
        await _dbHelper.insertItem('sentence_explanations', expl);
        await _loadRelatedItems();
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Import Detail'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (_selectedText.isNotEmpty)
            TextButton.icon(
              onPressed: _explainSelection,
              icon: const Icon(Icons.auto_awesome, color: Colors.teal),
              label: const Text(
                "Explain",
                style: TextStyle(color: Colors.teal),
              ),
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Original Content (Select text to explain)',
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
                    child: SelectionArea(
                      onSelectionChanged: (val) {
                        setState(() {
                          _selectedText = val?.plainText ?? '';
                        });
                      },
                      child: Text(
                        widget.content,
                        style: const TextStyle(fontSize: 16),
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  // Show generate definition button for words without definitions
                  if (_importedContent?['content_type'] == 'word' && 
                      _definitions.isEmpty) ...[
                    Center(
                      child: ElevatedButton.icon(
                        onPressed: _isGeneratingDefinition 
                            ? null 
                            : _showGenerateDefinitionDialog,
                        icon: _isGeneratingDefinition
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.auto_awesome),
                        label: Text(_isGeneratingDefinition 
                            ? 'Generating...' 
                            : 'Generate Definition'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],
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
    final difficultyLevel = def['difficulty_level'] as int? ?? 0;
    final hasExamples = def['examples'] != null && 
        def['examples'].toString().isNotEmpty &&
        def['examples'] != '[]';
    
    List<WordExample>? examples;
    if (hasExamples) {
      try {
        final examplesJson = def['examples'] is String
            ? jsonDecode(def['examples'] as String)
            : def['examples'];
        examples = (examplesJson as List<dynamic>)
            .map((e) => WordExample.fromJson(e as Map<String, dynamic>))
            .toList();
      } catch (e) {
        examples = null;
      }
    }
    
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
                Expanded(
                  child: Text(
                    def['word'] ?? '',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.refresh, color: Colors.blue),
                      tooltip: 'Regenerate',
                      onPressed: _isGeneratingDefinition 
                          ? null 
                          : _showGenerateDefinitionDialog,
                    ),
                    IconButton(
                      icon: const Icon(
                        Icons.add_circle_outline,
                        color: Colors.teal,
                      ),
                      onPressed: () => _addToDeck(def, true),
                    ),
                  ),
                ),
              ],
            ),
            const Divider(),
            Text(def['definition'] ?? '', style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 12),
            Row(
              children: [
                const Text('Difficulty: ', style: TextStyle(fontWeight: FontWeight.bold)),
                ...List.generate(5, (index) {
                  return IconButton(
                    icon: Icon(
                      index < difficultyLevel ? Icons.star : Icons.star_border,
                      color: _getDifficultyColor(difficultyLevel),
                      size: 20,
                    ),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    onPressed: () => _updateDifficulty(def['id'] as int, index + 1),
                  );
                }),
              ],
            ),
            const SizedBox(height: 12),
            if (examples != null && examples.isNotEmpty) ...[
              ExpansionTile(
                title: const Text(
                  'Examples',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                initiallyExpanded: false,
                children: examples.map((example) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          example.sentence,
                          style: const TextStyle(
                            fontStyle: FontStyle.italic,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          example.translation,
                          style: TextStyle(
                            color: Colors.grey[700],
                            fontSize: 14,
                          ),
                        ),
                        if (example != examples.last) const Divider(),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ] else ...[
              Center(
                child: TextButton.icon(
                  onPressed: _isGeneratingExamples
                      ? null
                      : () => _generateExamples(def['id'] as int),
                  icon: _isGeneratingExamples
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.lightbulb_outline),
                  label: Text(_isGeneratingExamples 
                      ? 'Generating...' 
                      : 'Generate Examples'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Color _getDifficultyColor(int difficulty) {
    if (difficulty <= 1) return Colors.green;
    if (difficulty <= 3) return Colors.orange;
    return Colors.red;
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
