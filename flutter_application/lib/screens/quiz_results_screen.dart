import 'package:flutter/material.dart';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/quiz_service.dart';

class QuizResultsScreen extends StatefulWidget {
  final int sessionId;
  final String deckName;

  const QuizResultsScreen({
    super.key,
    required this.sessionId,
    required this.deckName,
  });

  @override
  State<QuizResultsScreen> createState() => _QuizResultsScreenState();
}

class _QuizResultsScreenState extends State<QuizResultsScreen> {
  final QuizService _quizService = QuizService();
  
  QuizSession? _session;
  List<QuizQuestion> _questions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadResults();
  }

  Future<void> _loadResults() async {
    setState(() => _isLoading = true);
    
    try {
      final results = await _quizService.getQuizResults(widget.sessionId);
      
      setState(() {
        _session = results['session'];
        _questions = results['questions'];
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading results: $e')),
        );
        Navigator.pop(context);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Quiz Results'),
        ),
        body: const Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_session == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Quiz Results'),
        ),
        body: const Center(
          child: Text('No results available'),
        ),
      );
    }

    final score = _session!.score ?? 0;
    final total = _session!.totalQuestions ?? 0;
    final correctCount = _questions.where((q) => q.isCorrect == 1).length;
    final incorrectCount = _questions.where((q) => q.isCorrect == 0).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Quiz Results'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () {
            Navigator.popUntil(context, (route) => route.isFirst);
          },
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Score card
          Card(
            elevation: 4,
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const Icon(
                    Icons.emoji_events,
                    size: 64,
                    color: Colors.amber,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '$score%',
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: _getScoreColor(score),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _getScoreMessage(score),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _StatItem(
                        icon: Icons.check_circle,
                        label: 'Correct',
                        value: correctCount.toString(),
                        color: Colors.green,
                      ),
                      _StatItem(
                        icon: Icons.cancel,
                        label: 'Incorrect',
                        value: incorrectCount.toString(),
                        color: Colors.red,
                      ),
                      _StatItem(
                        icon: Icons.quiz,
                        label: 'Total',
                        value: total.toString(),
                        color: Colors.blue,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          
          // Review section
          Text(
            'Review Questions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          
          ..._questions.asMap().entries.map((entry) {
            final index = entry.key;
            final question = entry.value;
            final isCorrect = question.isCorrect == 1;
            
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ExpansionTile(
                leading: Icon(
                  isCorrect ? Icons.check_circle : Icons.cancel,
                  color: isCorrect ? Colors.green : Colors.red,
                ),
                title: Text('Question ${index + 1}'),
                subtitle: Text(
                  question.questionText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          question.questionText,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 16),
                        
                        _buildChoiceItem(
                          'A',
                          question.choiceA,
                          question.correctAnswer,
                          question.userAnswer,
                        ),
                        _buildChoiceItem(
                          'B',
                          question.choiceB,
                          question.correctAnswer,
                          question.userAnswer,
                        ),
                        _buildChoiceItem(
                          'C',
                          question.choiceC,
                          question.correctAnswer,
                          question.userAnswer,
                        ),
                        _buildChoiceItem(
                          'D',
                          question.choiceD,
                          question.correctAnswer,
                          question.userAnswer,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
          
          const SizedBox(height: 24),
          
          // Action buttons
          ElevatedButton.icon(
            onPressed: () {
              Navigator.popUntil(context, (route) => route.isFirst);
            },
            icon: const Icon(Icons.home),
            label: const Text('Back to Home'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.all(16),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChoiceItem(
    String letter,
    String? text,
    String? correctAnswer,
    String? userAnswer,
  ) {
    if (text == null) return const SizedBox.shrink();
    
    final isCorrect = letter == correctAnswer;
    final isUserAnswer = letter == userAnswer;
    
    Color? backgroundColor;
    Widget? trailing;
    
    if (isCorrect) {
      backgroundColor = Colors.green[100];
      trailing = const Icon(Icons.check, color: Colors.green);
    } else if (isUserAnswer) {
      backgroundColor = Colors.red[100];
      trailing = const Icon(Icons.close, color: Colors.red);
    }
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: backgroundColor,
        border: Border.all(
          color: isCorrect
              ? Colors.green
              : isUserAnswer
                  ? Colors.red
                  : Colors.grey[300]!,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Text(
            '$letter. ',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          Expanded(child: Text(text)),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  Color _getScoreColor(int score) {
    if (score >= 90) return Colors.green;
    if (score >= 70) return Colors.blue;
    if (score >= 50) return Colors.orange;
    return Colors.red;
  }

  String _getScoreMessage(int score) {
    if (score >= 90) return 'Excellent! 🎉';
    if (score >= 70) return 'Good job! 👍';
    if (score >= 50) return 'Keep practicing! 💪';
    return 'Review the material 📚';
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatItem({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}
