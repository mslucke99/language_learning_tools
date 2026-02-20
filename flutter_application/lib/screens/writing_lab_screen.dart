import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../services/writing_service.dart';
import '../services/llm_service.dart';

class WritingLabScreen extends StatefulWidget {
  final WritingSession? session;
  final String? language;

  const WritingLabScreen({super.key, this.session, this.language});

  @override
  State<WritingLabScreen> createState() => _WritingLabScreenState();
}

class _WritingLabScreenState extends State<WritingLabScreen> {
  late WritingService _writingService;
  final TextEditingController _topicController = TextEditingController();
  final TextEditingController _textController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();

  bool _isLoading = false;
  bool _showFeedback = false;
  Map<String, dynamic>? _feedback;
  int? _sessionId;

  @override
  void initState() {
    super.initState();
    final llmService = Provider.of<LLMService>(context, listen: false);
    _writingService = WritingService(llmService);

    if (widget.session != null) {
      _loadSession();
    }
  }

  void _loadSession() {
    final session = widget.session!;
    _sessionId = session.id;
    _topicController.text = session.topic;
    _textController.text = session.userWriting;
    _notesController.text = session.userNotes ?? '';

    if (session.analysis != null) {
      try {
        _feedback = json.decode(session.analysis!);
        _showFeedback = true;
      } catch (e) {
        // Invalid JSON, ignore
      }
    }
  }

  Future<void> _submitForFeedback() async {
    if (_textController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please write something first')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // Create session if needed
      if (_sessionId == null) {
        _sessionId = await _writingService.createSession(
          _topicController.text.isEmpty ? 'Untitled' : _topicController.text,
          widget.language ?? 'Unknown',
        );
      }

      // Get feedback
      final analysis = await _writingService.submitForFeedback(
        _sessionId!,
        _textController.text,
        widget.language ?? 'Unknown',
        _topicController.text,
      );

      // Save session
      await _writingService.saveSession(
        _sessionId!,
        _textController.text,
        analysis['raw_feedback'] as String?,
        analysis['grade'] as String?,
        json.encode(analysis),
      );

      setState(() {
        _feedback = analysis;
        _showFeedback = true;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _saveDraft() async {
    try {
      if (_sessionId == null) {
        _sessionId = await _writingService.createSession(
          _topicController.text.isEmpty ? 'Untitled' : _topicController.text,
          widget.language ?? 'Unknown',
        );
      }

      await _writingService.saveSession(
        _sessionId!,
        _textController.text,
        null,
        null,
        null,
      );

      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Draft saved')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error saving: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Writing Lab'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveDraft,
            tooltip: 'Save Draft',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _topicController,
                    decoration: const InputDecoration(
                      labelText: 'Topic',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _textController,
                    decoration: const InputDecoration(
                      labelText: 'Your Writing',
                      border: OutlineInputBorder(),
                      alignLabelWithHint: true,
                    ),
                    maxLines: 15,
                    minLines: 10,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _submitForFeedback,
                    icon: const Icon(Icons.send),
                    label: const Text('Submit for Feedback'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.all(16),
                    ),
                  ),
                  if (_showFeedback && _feedback != null) ...[
                    const SizedBox(height: 24),
                    _buildFeedbackSection(),
                  ],
                  const SizedBox(height: 16),
                  TextField(
                    controller: _notesController,
                    decoration: const InputDecoration(
                      labelText: 'Personal Notes',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 3,
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildFeedbackSection() {
    final grade = _feedback!['grade'] as String? ?? 'N/A';
    final strengths = _feedback!['strengths'] as List? ?? [];
    final improvements = _feedback!['improvements'] as List? ?? [];
    final suggestions = _feedback!['suggestions'] as List? ?? [];

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.grade, color: Colors.teal),
                const SizedBox(width: 8),
                Text(
                  'Grade: $grade',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Colors.teal,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            if (strengths.isNotEmpty) ...[
              Text(
                'Strengths',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                ),
              ),
              const SizedBox(height: 8),
              ...strengths.map(
                (s) => Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('✓ ', style: TextStyle(color: Colors.green)),
                      Expanded(child: Text(s.toString())),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (improvements.isNotEmpty) ...[
              Text(
                'Areas for Improvement',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.orange,
                ),
              ),
              const SizedBox(height: 8),
              ...improvements.map(
                (i) => Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• ', style: TextStyle(color: Colors.orange)),
                      Expanded(child: Text(i.toString())),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (suggestions.isNotEmpty) ...[
              Text(
                'Suggestions',
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...suggestions.map((s) => _buildSuggestionCard(s)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionCard(dynamic suggestion) {
    if (suggestion is! Map) return const SizedBox();

    final original = suggestion['original'] as String? ?? '';
    final corrected = suggestion['corrected'] as String? ?? '';
    final explanation = suggestion['explanation'] as String? ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (original.isNotEmpty)
              Text(
                '❌ $original',
                style: const TextStyle(
                  decoration: TextDecoration.lineThrough,
                  color: Colors.red,
                ),
              ),
            if (corrected.isNotEmpty)
              Text(
                '✓ $corrected',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                ),
              ),
            if (explanation.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                explanation,
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _topicController.dispose();
    _textController.dispose();
    _notesController.dispose();
    super.dispose();
  }
}
