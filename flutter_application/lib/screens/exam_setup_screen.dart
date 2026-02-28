import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/exam_service.dart';
import '../services/llm_service.dart';
import 'exam_taking_screen.dart';

class ExamSetupScreen extends StatefulWidget {
  final String language;

  const ExamSetupScreen({
    super.key,
    required this.language,
  });

  @override
  State<ExamSetupScreen> createState() => _ExamSetupScreenState();
}

class _ExamSetupScreenState extends State<ExamSetupScreen> {
  late ExamService _examService;
  
  String? _selectedExam;
  String? _selectedLevel;
  String? _selectedSection;
  int _questionCount = 10;
  bool _timerEnabled = false;
  bool _isGenerating = false;

  @override
  void initState() {
    super.initState();
    final llmService = Provider.of<LLMService>(context, listen: false);
    _examService = ExamService(llmService);
  }

  @override
  Widget build(BuildContext context) {
    final examTypes = _examService.getExamTypes();
    final levels = _selectedExam != null
        ? _examService.getLevelsForExam(_selectedExam!)
        : <String>[];
    final sections = _selectedExam != null
        ? _examService.getSectionsForExam(_selectedExam!)
        : <String>[];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Exam Practice Setup'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isGenerating
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Generating exam questions...'),
                ],
              ),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    value: _selectedExam,
                    decoration: const InputDecoration(
                      labelText: 'Exam Type',
                      border: OutlineInputBorder(),
                    ),
                    items: examTypes.map((exam) => DropdownMenuItem(
                      value: exam,
                      child: Text(exam),
                    )).toList(),
                    onChanged: (value) {
                      setState(() {
                        _selectedExam = value;
                        _selectedLevel = null;
                        _selectedSection = null;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedLevel,
                    decoration: const InputDecoration(
                      labelText: 'Level',
                      border: OutlineInputBorder(),
                    ),
                    items: levels.map((level) => DropdownMenuItem(
                      value: level,
                      child: Text(level),
                    )).toList(),
                    onChanged: _selectedExam == null
                        ? null
                        : (value) => setState(() => _selectedLevel = value),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedSection,
                    decoration: const InputDecoration(
                      labelText: 'Section',
                      border: OutlineInputBorder(),
                    ),
                    items: sections.map((section) => DropdownMenuItem(
                      value: section,
                      child: Text(section),
                    )).toList(),
                    onChanged: _selectedExam == null
                        ? null
                        : (value) => setState(() => _selectedSection = value),
                  ),
                  const SizedBox(height: 16),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Number of Questions: $_questionCount',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Slider(
                            value: _questionCount.toDouble(),
                            min: 5,
                            max: 50,
                            divisions: 9,
                            label: _questionCount.toString(),
                            onChanged: (value) => setState(() => _questionCount = value.toInt()),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Enable Timer'),
                    subtitle: const Text('Time limit based on exam type'),
                    value: _timerEnabled,
                    onChanged: (value) => setState(() => _timerEnabled = value),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: _canStartExam() ? _startExam : null,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Exam'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.all(16),
                      backgroundColor: Colors.deepPurple,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  bool _canStartExam() {
    return _selectedExam != null &&
        _selectedLevel != null &&
        _selectedSection != null &&
        !_isGenerating;
  }

  Future<void> _startExam() async {
    setState(() => _isGenerating = true);

    try {
      final attemptId = await _examService.generateExam(
        examName: _selectedExam!,
        level: _selectedLevel!,
        section: _selectedSection!,
        questionCount: _questionCount,
        language: widget.language,
      );

      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => ExamTakingScreen(
              attemptId: attemptId,
              timerEnabled: _timerEnabled,
            ),
          ),
        );
      }
    } catch (e) {
      setState(() => _isGenerating = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }
}
