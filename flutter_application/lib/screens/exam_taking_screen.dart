import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../services/exam_service.dart';
import '../services/llm_service.dart';
import 'exam_results_screen.dart';

class ExamTakingScreen extends StatefulWidget {
  final int attemptId;
  final bool timerEnabled;

  const ExamTakingScreen({
    super.key,
    required this.attemptId,
    this.timerEnabled = false,
  });

  @override
  State<ExamTakingScreen> createState() => _ExamTakingScreenState();
}

class _ExamTakingScreenState extends State<ExamTakingScreen> {
  late ExamService _examService;
  
  List<ExamQuestion> _questions = [];
  int _currentQuestionIndex = 0;
  bool _isLoading = true;
  bool _showExplanation = false;
  String? _selectedAnswer;
  
  Timer? _timer;
  int _secondsRemaining = 3600; // 60 minutes default
  
  @override
  void initState() {
    super.initState();
    final llmService = Provider.of<LLMService>(context, listen: false);
    _examService = ExamService(llmService);
    _loadQuestions();
    
    if (widget.timerEnabled) {
      _startTimer();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_secondsRemaining > 0) {
        setState(() => _secondsRemaining--);
      } else {
        _timer?.cancel();
        _finishExam();
      }
    });
  }

  Future<void> _loadQuestions() async {
    setState(() => _isLoading = true);
    
    try {
      final questions = await _examService.getExamQuestions(widget.attemptId);
      
      setState(() {
        _questions = questions;
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

  Future<void> _submitAnswer() async {
    if (_selectedAnswer == null) return;
    
    final currentQuestion = _questions[_currentQuestionIndex];
    
    try {
      await _examService.submitAnswer(currentQuestion.id!, _selectedAnswer!);
      
      setState(() {
        _showExplanation = true;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _nextQuestion() {
    if (_currentQuestionIndex < _questions.length - 1) {
      setState(() {
        _currentQuestionIndex++;
        _selectedAnswer = null;
        _showExplanation = false;
      });
    } else {
      _finishExam();
    }
  }

  Future<void> _finishExam() async {
    _timer?.cancel();
    
    try {
      await _examService.calculateScore(widget.attemptId);
      
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => ExamResultsScreen(attemptId: widget.attemptId),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  String _formatTime(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Exam')),
        body: const Center(child: Text('No questions available')),
      );
    }

    final currentQuestion = _questions[_currentQuestionIndex];
    final progress = (_currentQuestionIndex + 1) / _questions.length;

    return WillPopScope(
      onWillPop: () async {
        final confirm = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Exit Exam?'),
            content: const Text('Your progress will be lost if you exit now.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Exit', style: TextStyle(color: Colors.red)),
              ),
            ],
          ),
        );
        return confirm ?? false;
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('Question ${_currentQuestionIndex + 1}/${_questions.length}'),
          backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          actions: widget.timerEnabled
              ? [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Center(
                      child: Text(
                        _formatTime(_secondsRemaining),
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _secondsRemaining < 300 ? Colors.red : Colors.black,
                        ),
                      ),
                    ),
                  ),
                ]
              : null,
        ),
        body: Column(
          children: [
            LinearProgressIndicator(value: progress),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      currentQuestion.questionText,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 32),
                    _buildChoiceButton('A', currentQuestion.choiceA),
                    const SizedBox(height: 12),
                    _buildChoiceButton('B', currentQuestion.choiceB),
                    const SizedBox(height: 12),
                    _buildChoiceButton('C', currentQuestion.choiceC),
                    const SizedBox(height: 12),
                    _buildChoiceButton('D', currentQuestion.choiceD),
                    if (_showExplanation && currentQuestion.explanation != null) ...[
                      const SizedBox(height: 32),
                      Card(
                        color: _selectedAnswer == currentQuestion.correctAnswer
                            ? Colors.green.shade50
                            : Colors.red.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    _selectedAnswer == currentQuestion.correctAnswer
                                        ? Icons.check_circle
                                        : Icons.cancel,
                                    color: _selectedAnswer == currentQuestion.correctAnswer
                                        ? Colors.green
                                        : Colors.red,
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    _selectedAnswer == currentQuestion.correctAnswer
                                        ? 'Correct!'
                                        : 'Incorrect',
                                    style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                      color: _selectedAnswer == currentQuestion.correctAnswer
                                          ? Colors.green
                                          : Colors.red,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'Correct Answer: ${currentQuestion.correctAnswer}',
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 8),
                              Text(currentQuestion.explanation!),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.grey.withOpacity(0.2),
                    spreadRadius: 1,
                    blurRadius: 3,
                    offset: const Offset(0, -1),
                  ),
                ],
              ),
              child: Row(
                children: [
                  if (_showExplanation)
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _nextQuestion,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.all(16),
                        ),
                        child: Text(
                          _currentQuestionIndex < _questions.length - 1
                              ? 'Next Question'
                              : 'Finish Exam',
                        ),
                      ),
                    )
                  else
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _selectedAnswer != null ? _submitAnswer : null,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.all(16),
                        ),
                        child: const Text('Submit Answer'),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChoiceButton(String letter, String? text) {
    if (text == null) return const SizedBox();

    final isSelected = _selectedAnswer == letter;
    final isCorrect = letter == _questions[_currentQuestionIndex].correctAnswer;
    final showResult = _showExplanation;

    Color? backgroundColor;
    Color? borderColor;
    
    if (showResult) {
      if (isCorrect) {
        backgroundColor = Colors.green.shade100;
        borderColor = Colors.green;
      } else if (isSelected) {
        backgroundColor = Colors.red.shade100;
        borderColor = Colors.red;
      }
    } else if (isSelected) {
      backgroundColor = Colors.blue.shade100;
      borderColor = Colors.blue;
    }

    return OutlinedButton(
      onPressed: _showExplanation ? null : () {
        setState(() => _selectedAnswer = letter);
      },
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.all(16),
        backgroundColor: backgroundColor,
        side: BorderSide(
          color: borderColor ?? Colors.grey,
          width: borderColor != null ? 2 : 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: borderColor ?? Colors.grey.shade300,
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
        ],
      ),
    );
  }
}
