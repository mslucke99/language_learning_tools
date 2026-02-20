import 'package:flutter/material.dart';
import 'package:proficiency_suites/services/deck_service.dart';

class FlashcardEditorScreen extends StatefulWidget {
  final int deckId;
  final int? flashcardId; // null for new flashcard
  final String? initialQuestion;
  final String? initialAnswer;

  const FlashcardEditorScreen({
    super.key,
    required this.deckId,
    this.flashcardId,
    this.initialQuestion,
    this.initialAnswer,
  });

  @override
  State<FlashcardEditorScreen> createState() => _FlashcardEditorScreenState();
}

class _FlashcardEditorScreenState extends State<FlashcardEditorScreen> {
  final DeckService _deckService = DeckService();
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _questionController;
  late TextEditingController _answerController;

  bool _isSaving = false;
  bool _showPreview = false;

  @override
  void initState() {
    super.initState();
    _questionController = TextEditingController(text: widget.initialQuestion);
    _answerController = TextEditingController(text: widget.initialAnswer);
  }

  @override
  void dispose() {
    _questionController.dispose();
    _answerController.dispose();
    super.dispose();
  }

  Future<void> _saveFlashcard() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSaving = true);

    try {
      if (widget.flashcardId == null) {
        // Create new flashcard
        await _deckService.addFlashcard(
          deckId: widget.deckId,
          question: _questionController.text.trim(),
          answer: _answerController.text.trim(),
        );

        if (mounted) {
          Navigator.pop(context, true);
        }
      } else {
        // Update existing flashcard
        await _deckService.updateFlashcard(
          widget.flashcardId!,
          question: _questionController.text.trim(),
          answer: _answerController.text.trim(),
        );

        if (mounted) {
          Navigator.pop(context, true);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error saving flashcard: $e')));
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isNewCard = widget.flashcardId == null;

    return Scaffold(
      appBar: AppBar(
        title: Text(isNewCard ? 'New Flashcard' : 'Edit Flashcard'),
        actions: [
          IconButton(
            icon: Icon(_showPreview ? Icons.edit : Icons.preview),
            onPressed: () {
              setState(() => _showPreview = !_showPreview);
            },
          ),
          if (_isSaving)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: CircularProgressIndicator(color: Colors.white),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.check),
              onPressed: _saveFlashcard,
            ),
        ],
      ),
      body: _showPreview ? _buildPreview() : _buildEditor(),
    );
  }

  Widget _buildEditor() {
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Question (Front)',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _questionController,
            decoration: const InputDecoration(
              hintText: 'Enter the question or term',
              border: OutlineInputBorder(),
            ),
            maxLines: 5,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Please enter a question';
              }
              return null;
            },
            enabled: !_isSaving,
          ),
          const SizedBox(height: 24),

          const Text(
            'Answer (Back)',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _answerController,
            decoration: const InputDecoration(
              hintText: 'Enter the answer or definition',
              border: OutlineInputBorder(),
            ),
            maxLines: 5,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Please enter an answer';
              }
              return null;
            },
            enabled: !_isSaving,
          ),
          const SizedBox(height: 24),

          ElevatedButton.icon(
            onPressed: _isSaving ? null : _saveFlashcard,
            icon: const Icon(Icons.save),
            label: Text(
              widget.flashcardId == null ? 'Create Flashcard' : 'Save Changes',
            ),
            style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
          ),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    return Center(
      child: Card(
        margin: const EdgeInsets.all(32),
        elevation: 8,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 400, maxHeight: 500),
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'Question',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _questionController.text.isEmpty
                    ? '(No question)'
                    : _questionController.text,
                style: const TextStyle(fontSize: 20),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              const Divider(),
              const SizedBox(height: 32),
              const Text(
                'Answer',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _answerController.text.isEmpty
                    ? '(No answer)'
                    : _answerController.text,
                style: const TextStyle(fontSize: 20, color: Colors.teal),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
