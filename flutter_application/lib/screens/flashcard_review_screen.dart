import 'package:flutter/material.dart';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/flashcard_review_service.dart';

class FlashcardReviewScreen extends StatefulWidget {
  final int deckId;
  final String deckName;

  const FlashcardReviewScreen({
    super.key,
    required this.deckId,
    required this.deckName,
  });

  @override
  State<FlashcardReviewScreen> createState() => _FlashcardReviewScreenState();
}

class _FlashcardReviewScreenState extends State<FlashcardReviewScreen> {
  final FlashcardReviewService _reviewService = FlashcardReviewService();
  
  List<Flashcard> _cards = [];
  int _currentIndex = 0;
  bool _showAnswer = false;
  bool _isLoading = true;
  DateTime? _reviewStartTime;
  
  int _reviewedCount = 0;
  int _correctCount = 0;

  @override
  void initState() {
    super.initState();
    _loadDueCards();
  }

  Future<void> _loadDueCards() async {
    setState(() => _isLoading = true);
    
    try {
      final cards = await _reviewService.getDueCards(widget.deckId);
      
      if (cards.isEmpty) {
        if (mounted) {
          _showNoCardsDialog();
        }
        return;
      }
      
      setState(() {
        _cards = cards;
        _currentIndex = 0;
        _showAnswer = false;
        _isLoading = false;
        _reviewStartTime = DateTime.now();
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading cards: $e')),
        );
        Navigator.pop(context);
      }
    }
  }

  void _showNoCardsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('No Cards Due'),
        content: const Text('All cards have been reviewed! Come back later.'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Go back
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _toggleAnswer() {
    setState(() {
      _showAnswer = !_showAnswer;
    });
  }

  Future<void> _rateCard(int quality) async {
    if (_currentIndex >= _cards.length) return;
    
    final card = _cards[_currentIndex];
    final timeTaken = _reviewStartTime != null
        ? DateTime.now().difference(_reviewStartTime!).inSeconds
        : 0;
    
    try {
      await _reviewService.rateCard(card, quality, timeTaken);
      
      setState(() {
        _reviewedCount++;
        if (quality >= 3) {
          _correctCount++;
        }
        
        _currentIndex++;
        _showAnswer = false;
        _reviewStartTime = DateTime.now();
      });
      
      if (_currentIndex >= _cards.length) {
        _showCompletionDialog();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving review: $e')),
        );
      }
    }
  }

  void _showCompletionDialog() {
    final accuracy = _reviewedCount > 0
        ? (_correctCount / _reviewedCount * 100).toStringAsFixed(1)
        : '0.0';
    
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('🎉 Review Complete!'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Cards reviewed: $_reviewedCount'),
            Text('Correct: $_correctCount'),
            Text('Accuracy: $accuracy%'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Go back
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(
          title: Text(widget.deckName),
        ),
        body: const Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_cards.isEmpty || _currentIndex >= _cards.length) {
      return Scaffold(
        appBar: AppBar(
          title: Text(widget.deckName),
        ),
        body: const Center(
          child: Text('No cards to review'),
        ),
      );
    }

    final card = _cards[_currentIndex];
    final progress = (_currentIndex + 1) / _cards.length;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deckName),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: Colors.grey[300],
          ),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Progress indicator
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Card ${_currentIndex + 1} of ${_cards.length}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    'Accuracy: ${_reviewedCount > 0 ? (_correctCount / _reviewedCount * 100).toStringAsFixed(0) : '0'}%',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
            ),
            
            // Card display
            Expanded(
              child: GestureDetector(
                onTap: _toggleAnswer,
                child: Card(
                  margin: const EdgeInsets.all(16.0),
                  elevation: 4,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Question
                        Text(
                          card.question,
                          style: Theme.of(context).textTheme.headlineSmall,
                          textAlign: TextAlign.center,
                        ),
                        
                        if (_showAnswer) ...[
                          const SizedBox(height: 32),
                          const Divider(),
                          const SizedBox(height: 32),
                          
                          // Answer
                          Text(
                            card.answer,
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: Colors.teal,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ] else ...[
                          const SizedBox(height: 32),
                          Text(
                            'Tap to reveal answer',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
            
            // Rating buttons
            if (_showAnswer)
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text(
                      'How well did you know this?',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: _RatingButton(
                            label: 'Again',
                            color: Colors.red,
                            onPressed: () => _rateCard(0),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: _RatingButton(
                            label: 'Hard',
                            color: Colors.orange,
                            onPressed: () => _rateCard(3),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: _RatingButton(
                            label: 'Good',
                            color: Colors.blue,
                            onPressed: () => _rateCard(4),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: _RatingButton(
                            label: 'Easy',
                            color: Colors.green,
                            onPressed: () => _rateCard(5),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: ElevatedButton(
                  onPressed: _toggleAnswer,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: const Text('Show Answer'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _RatingButton extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onPressed;

  const _RatingButton({
    required this.label,
    required this.color,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 12),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 14),
      ),
    );
  }
}
