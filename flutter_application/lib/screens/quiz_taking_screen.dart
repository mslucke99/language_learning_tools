import 'package:flutter/material.dart';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/quiz_service.dart';
import 'package:proficiency_suites/screens/quiz_results_screen.dart';

class QuizTakingScreen extends StatefulWidget {
  final int sessionId;
  final String deckName;

  const QuizTakingScreen({
    super.key,
    required this.sessionId,
    required this.deckName,
  });

  @override
  State<QuizTakingScreen> createState() => _QuizTakingScreenState();
}

class _QuizTakingScreenState extends State<QuizTakingScreen> {
  final QuizService _quizService = QuizService();
  
  List<QuizQuestion> _questions = [];
  int _currentIndex = 0;
  String? _selectedAnswer;
  bool _showFeedback = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadQuestions();
  }

  Future<void> _loadQuestions() async {
    setState(() => _isLoading = true);
    
    try {
      final questions = await _quizService.getQuizQuestions(widget.sessionId);
      
      setState(() {
        _questions = questions;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading questions: $e')),
        );
        Navigator.pop(context);
      }
    }
  }

  Future<void> _submitAnswer() async {
    if (_selectedAnswer == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an answer')),
      );
      return;
    }
    
    try {
      final question = _questions[_currentIndex];
      final isCorrect = await _quizService.submitAnswer(
        question.id!,
        _selectedAnswer!,
      );
      
      setState(() {
        _showFeedback = true;
      });
      
      // Auto-advance after showing feedback
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          _nextQuestion();
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error submitting answer: $e')),
        );
      }
    }
  }

  void _nextQuestion() {
    if (_currentIndex < _questions.length - 1) {
      setState(() {
        _currentIndex++;
        _selectedAnswer = null;
        _showFeedback = false;
      });
    } else {
      _finishQuiz();
    }
  }

  Future<void> _finishQuiz() async {
    try {
      final score = await _quizService.calculateScore(widget.sessionId);
      
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => QuizResultsScreen(
              sessionId: widget.sessionId,
              deckName: widget.deckName,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error calculating score: $e')),
        );
      }
    }
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

    if (_questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: Text(widget.deckName),
        ),
        body: const Center(
          child: Text('No questions available'),
        ),
      );
    }

    final question = _questions[_currentIndex];
    final progress = (_currentIndex + 1) / _questions.length;
    final choices = {
      'A': question.choiceA,
      'B': question.choiceB,
      'C': question.choiceC,
      'D': question.choiceD,
    };

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
              child: Text(
                'Question ${_currentIndex + 1} of ${_questions.length}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            
            // Question
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Card(
                      elevation: 2,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          question.questionText,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    
                    // Choices
                    ...choices.entries.map((entry) {
                      final letter = entry.key;
                      final text = entry.value;
                      
                      if (text == null) return const SizedBox.shrink();
                      
                      final isSelected = _selectedAnswer == letter;
                      final isCorrect = question.correctAnswer == letter;
                      
                      Color? backgroundColor;
                      Color? borderColor;
                      
                      if (_showFeedback) {
                        if (isCorrect) {
                          backgroundColor = Colors.green[100];
                          borderColor = Colors.green;
                        } else if (isSelected) {
                          backgroundColor = Colors.red[100];
                          borderColor = Colors.red;
                        }
                      } else if (isSelected) {
                        backgroundColor = Colors.blue[50];
                        borderColor = Colors.blue;
                      }
                      
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: InkWell(
                          onTap: _showFeedback
                              ? null
                              : () {
                                  setState(() => _selectedAnswer = letter);
                                },
                          child: Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: backgroundColor,
                              border: Border.all(
                                color: borderColor ?? Colors.grey[300]!,
                                width: 2,
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  width: 32,
                                  height: 32,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: borderColor ?? Colors.grey[300],
                                  ),
                                  child: Center(
                                    child: Text(
                                      letter,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: Text(
                                    text,
                                    style: const TextStyle(fontSize: 16),
                                  ),
                                ),
                                if (_showFeedback && isCorrect)
                                  const Icon(Icons.check_circle, color: Colors.green),
                                if (_showFeedback && isSelected && !isCorrect)
                                  const Icon(Icons.cancel, color: Colors.red),
                              ],
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ),
            
            // Submit button
            if (!_showFeedback)
              Padding(
                padding: const EdgeInsets.all(16),
                child: ElevatedButton(
                  onPressed: _selectedAnswer == null ? null : _submitAnswer,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: const Text('Submit Answer'),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.all(16),
                child: ElevatedButton(
                  onPressed: _nextQuestion,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 50),
                  ),
                  child: Text(
                    _currentIndex < _questions.length - 1
                        ? 'Next Question'
                        : 'Finish Quiz',
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
