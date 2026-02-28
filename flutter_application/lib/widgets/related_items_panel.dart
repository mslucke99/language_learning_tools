/// Related Items Panel Widget
/// 
/// Displays AI-generated suggestions (flashcards and grammar patterns)
/// with actions to add them to decks, vocab lists, or grammar books.

import 'package:flutter/material.dart';
import '../models/suggestions.dart';
import '../services/database_helper.dart';
import 'suggestion_card.dart';

class RelatedItemsPanel extends StatefulWidget {
  final Suggestions suggestions;
  final VoidCallback? onItemAdded;
  
  const RelatedItemsPanel({
    super.key,
    required this.suggestions,
    this.onItemAdded,
  });
  
  @override
  State<RelatedItemsPanel> createState() => _RelatedItemsPanelState();
}

class _RelatedItemsPanelState extends State<RelatedItemsPanel> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  final Set<String> _addedFlashcards = {};
  final Set<String> _addedGrammar = {};
  
  Future<void> _addFlashcardToDeck(FlashcardSuggestion suggestion) async {
    // Load available decks
    final db = await _dbHelper.database;
    final decks = await db.query(
      'decks',
      where: 'deleted_at IS NULL',
      orderBy: 'name ASC',
    );
    
    if (decks.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No decks available. Create a deck first.')),
        );
      }
      return;
    }
    
    // Show deck picker
    final selectedDeck = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Deck'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: decks.length,
            itemBuilder: (context, index) {
              final deck = decks[index];
              return ListTile(
                title: Text(deck['name'] as String),
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
    
    if (selectedDeck == null) return;
    
    // Add flashcard to deck
    try {
      await _dbHelper.insertItem('flashcards', {
        'deck_id': selectedDeck['id'],
        'question': suggestion.word,
        'answer': suggestion.definition,
        'user_notes': suggestion.context ?? '',
      });
      
      setState(() {
        _addedFlashcards.add(suggestion.word);
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Added "${suggestion.word}" to ${selectedDeck['name']}'),
          ),
        );
      }
      
      widget.onItemAdded?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding flashcard: $e')),
        );
      }
    }
  }
  
  Future<void> _addFlashcardToVocabList(FlashcardSuggestion suggestion) async {
    try {
      final now = DateTime.now().toIso8601String();
      
      // Create imported_content entry
      final contentId = await _dbHelper.insertItem('imported_content', {
        'content_type': 'word',
        'content': suggestion.word,
        'context': suggestion.context,
        'url': 'suggestion',
        'language': 'es', // TODO: Get from context
        'created_at': now,
        'processed': 0,
      });
      
      // Create word_definition entry
      await _dbHelper.insertItem('word_definitions', {
        'imported_content_id': contentId,
        'word': suggestion.word,
        'definition': suggestion.definition,
        'definition_language': 'native',
        'source': 'suggestion',
        'created_at': now,
        'last_updated': now,
      });
      
      setState(() {
        _addedFlashcards.add(suggestion.word);
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Added "${suggestion.word}" to vocabulary list')),
        );
      }
      
      widget.onItemAdded?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding to vocab list: $e')),
        );
      }
    }
  }
  
  Future<void> _addGrammarToBook(GrammarSuggestion suggestion) async {
    try {
      final now = DateTime.now().toIso8601String();
      
      await _dbHelper.insertItem('grammar_book_entries', {
        'title': suggestion.title,
        'explanation': suggestion.explanation,
        'language': 'es', // TODO: Get from context
        'source': 'suggestion',
        'created_at': now,
        'last_updated': now,
      });
      
      setState(() {
        _addedGrammar.add(suggestion.title);
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Added "${suggestion.title}" to grammar book')),
        );
      }
      
      widget.onItemAdded?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding to grammar book: $e')),
        );
      }
    }
  }
  
  Widget _buildEmptyState() {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.lightbulb_outline,
                size: 48,
                color: Colors.grey.shade400,
              ),
              const SizedBox(height: 16),
              Text(
                'No suggestions found',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey.shade600,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Generate an explanation to see vocabulary and grammar suggestions',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey.shade500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    if (widget.suggestions.isEmpty) {
      return _buildEmptyState();
    }
    
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Suggestions (${widget.suggestions.totalCount})',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            
            // Vocabulary section
            if (widget.suggestions.flashcards.isNotEmpty) ...[
              Row(
                children: [
                  const Icon(Icons.text_fields, color: Colors.orange),
                  const SizedBox(width: 8),
                  Text(
                    'Vocabulary (${widget.suggestions.flashcards.length})',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ...widget.suggestions.flashcards.map((flashcard) {
                return FlashcardSuggestionCard(
                  suggestion: flashcard,
                  isAdded: _addedFlashcards.contains(flashcard.word),
                  onAddToDeck: () => _addFlashcardToDeck(flashcard),
                  onAddToVocabList: () => _addFlashcardToVocabList(flashcard),
                );
              }),
              const SizedBox(height: 16),
            ],
            
            // Grammar section
            if (widget.suggestions.grammar.isNotEmpty) ...[
              Row(
                children: [
                  const Icon(Icons.menu_book, color: Colors.blue),
                  const SizedBox(width: 8),
                  Text(
                    'Grammar (${widget.suggestions.grammar.length})',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ...widget.suggestions.grammar.map((grammar) {
                return GrammarSuggestionCard(
                  suggestion: grammar,
                  isAdded: _addedGrammar.contains(grammar.title),
                  onAddToBook: () => _addGrammarToBook(grammar),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
