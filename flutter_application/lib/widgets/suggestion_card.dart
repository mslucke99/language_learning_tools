/// Suggestion Card Widgets
/// 
/// Reusable cards for displaying flashcard and grammar suggestions.

import 'package:flutter/material.dart';
import '../models/suggestions.dart';

/// Card for displaying a flashcard suggestion
class FlashcardSuggestionCard extends StatelessWidget {
  final FlashcardSuggestion suggestion;
  final bool isAdded;
  final VoidCallback onAddToDeck;
  final VoidCallback onAddToVocabList;
  
  const FlashcardSuggestionCard({
    super.key,
    required this.suggestion,
    required this.isAdded,
    required this.onAddToDeck,
    required this.onAddToVocabList,
  });
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: isAdded ? 0 : 1,
      color: isAdded ? Colors.grey.shade100 : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    suggestion.word,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: isAdded ? Colors.grey : Colors.black,
                    ),
                  ),
                ),
                if (isAdded)
                  const Icon(
                    Icons.check_circle,
                    color: Colors.green,
                    size: 20,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              suggestion.definition,
              style: TextStyle(
                fontSize: 14,
                color: isAdded ? Colors.grey.shade600 : Colors.grey.shade700,
              ),
            ),
            if (suggestion.context != null) ...[
              const SizedBox(height: 4),
              Text(
                'Context: ${suggestion.context}',
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey.shade600,
                ),
              ),
            ],
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: isAdded ? null : onAddToDeck,
                    icon: const Icon(Icons.add_circle_outline, size: 16),
                    label: const Text('Add to Deck'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: isAdded ? null : onAddToVocabList,
                    icon: const Icon(Icons.library_add, size: 16),
                    label: const Text('Add to Vocab'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Card for displaying a grammar suggestion
class GrammarSuggestionCard extends StatelessWidget {
  final GrammarSuggestion suggestion;
  final bool isAdded;
  final VoidCallback onAddToBook;
  
  const GrammarSuggestionCard({
    super.key,
    required this.suggestion,
    required this.isAdded,
    required this.onAddToBook,
  });
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: isAdded ? 0 : 1,
      color: isAdded ? Colors.grey.shade100 : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    suggestion.title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: isAdded ? Colors.grey : Colors.blue.shade700,
                    ),
                  ),
                ),
                if (isAdded)
                  const Icon(
                    Icons.check_circle,
                    color: Colors.green,
                    size: 20,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              suggestion.explanation,
              style: TextStyle(
                fontSize: 14,
                color: isAdded ? Colors.grey.shade600 : Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: isAdded ? null : onAddToBook,
                icon: const Icon(Icons.menu_book, size: 16),
                label: const Text('Add to Grammar Book'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
