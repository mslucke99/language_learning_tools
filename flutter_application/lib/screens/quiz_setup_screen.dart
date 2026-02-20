import 'package:flutter/material.dart';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/deck_service.dart';
import 'package:proficiency_suites/services/quiz_service.dart';
import 'package:proficiency_suites/screens/quiz_taking_screen.dart';

class QuizSetupScreen extends StatefulWidget {
  const QuizSetupScreen({super.key});

  @override
  State<QuizSetupScreen> createState() => _QuizSetupScreenState();
}

class _QuizSetupScreenState extends State<QuizSetupScreen> {
  final DeckService _deckService = DeckService();
  final QuizService _quizService = QuizService();
  
  List<Deck> _decks = [];
  Deck? _selectedDeck;
  int _questionCount = 10;
  String _difficulty = 'medium';
  bool _isLoading = true;
  bool _isGenerating = false;

  @override
  void initState() {
    super.initState();
    _loadDecks();
  }

  Future<void> _loadDecks() async {
    setState(() => _isLoading = true);
    
    try {
      final decks = await _deckService.getAllDecks();
      
      setState(() {
        _decks = decks;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading decks: $e')),
        );
      }
      setState(() => _isLoading = false);
    }
  }

  Future<void> _generateQuiz() async {
    if (_selectedDeck == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a deck')),
      );
      return;
    }
    
    setState(() => _isGenerating = true);
    
    try {
      final sessionId = await _quizService.generateQuiz(
        sourceType: 'deck',
        sourceId: _selectedDeck!.id!,
        questionCount: _questionCount,
        difficulty: _difficulty,
      );
      
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => QuizTakingScreen(
              sessionId: sessionId,
              deckName: _selectedDeck!.name,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error generating quiz: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Quiz Setup'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Text(
                  'Select Deck',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                
                DropdownButtonFormField<Deck>(
                  value: _selectedDeck,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.style),
                  ),
                  hint: const Text('Choose a deck'),
                  items: _decks.map((deck) {
                    return DropdownMenuItem(
                      value: deck,
                      child: Text(deck.name),
                    );
                  }).toList(),
                  onChanged: (deck) {
                    setState(() => _selectedDeck = deck);
                  },
                ),
                const SizedBox(height: 24),
                
                const Text(
                  'Number of Questions',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                
                Row(
                  children: [
                    Expanded(
                      child: Slider(
                        value: _questionCount.toDouble(),
                        min: 5,
                        max: 50,
                        divisions: 9,
                        label: _questionCount.toString(),
                        onChanged: (value) {
                          setState(() => _questionCount = value.round());
                        },
                      ),
                    ),
                    SizedBox(
                      width: 50,
                      child: Text(
                        _questionCount.toString(),
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                
                const Text(
                  'Difficulty',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(
                      value: 'easy',
                      label: Text('Easy'),
                      icon: Icon(Icons.sentiment_satisfied),
                    ),
                    ButtonSegment(
                      value: 'medium',
                      label: Text('Medium'),
                      icon: Icon(Icons.sentiment_neutral),
                    ),
                    ButtonSegment(
                      value: 'hard',
                      label: Text('Hard'),
                      icon: Icon(Icons.sentiment_very_dissatisfied),
                    ),
                  ],
                  selected: {_difficulty},
                  onSelectionChanged: (Set<String> selected) {
                    setState(() => _difficulty = selected.first);
                  },
                ),
                const SizedBox(height: 32),
                
                ElevatedButton.icon(
                  onPressed: _isGenerating ? null : _generateQuiz,
                  icon: _isGenerating
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.play_arrow),
                  label: Text(_isGenerating ? 'Generating...' : 'Start Quiz'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ],
            ),
    );
  }
}
