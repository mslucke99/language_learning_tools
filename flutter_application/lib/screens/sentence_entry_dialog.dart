/// Sentence Entry Dialog
/// 
/// Allows users to manually add sentences to their study list.
/// Sentences are saved to imported_content with content_type='sentence'.

import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class SentenceEntryDialog extends StatefulWidget {
  final String? initialLanguage;
  
  const SentenceEntryDialog({super.key, this.initialLanguage});
  
  @override
  State<SentenceEntryDialog> createState() => _SentenceEntryDialogState();
}

class _SentenceEntryDialogState extends State<SentenceEntryDialog> {
  final _formKey = GlobalKey<FormState>();
  final _sentenceController = TextEditingController();
  final _contextController = TextEditingController();
  final _urlController = TextEditingController();
  String? _selectedLanguage;
  bool _isSaving = false;
  
  final DatabaseHelper _dbHelper = DatabaseHelper();
  
  @override
  void initState() {
    super.initState();
    _selectedLanguage = widget.initialLanguage ?? 'es';
  }
  
  @override
  void dispose() {
    _sentenceController.dispose();
    _contextController.dispose();
    _urlController.dispose();
    super.dispose();
  }
  
  Future<int?> _saveSentence() async {
    if (!_formKey.currentState!.validate()) {
      return null;
    }
    
    setState(() {
      _isSaving = true;
    });
    
    try {
      final now = DateTime.now().toIso8601String();
      final sentenceId = await _dbHelper.insertItem('imported_content', {
        'content_type': 'sentence',
        'content': _sentenceController.text.trim(),
        'context': _contextController.text.trim().isEmpty 
            ? null 
            : _contextController.text.trim(),
        'url': _urlController.text.trim().isEmpty 
            ? 'manual_entry' 
            : _urlController.text.trim(),
        'language': _selectedLanguage,
        'created_at': now,
        'processed': 0,
      });
      
      if (mounted) {
        Navigator.pop(context, sentenceId);
      }
      
      return sentenceId;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving sentence: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return null;
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Sentence'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _sentenceController,
                decoration: const InputDecoration(
                  labelText: 'Sentence *',
                  hintText: 'Enter sentence to study',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
                maxLines: 3,
                autofocus: true,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Sentence is required';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _contextController,
                decoration: const InputDecoration(
                  labelText: 'Context (optional)',
                  hintText: 'e.g., "from conversation"',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _urlController,
                decoration: const InputDecoration(
                  labelText: 'Source URL (optional)',
                  hintText: 'https://...',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.url,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _selectedLanguage,
                decoration: const InputDecoration(
                  labelText: 'Language',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'es', child: Text('Spanish')),
                  DropdownMenuItem(value: 'fr', child: Text('French')),
                  DropdownMenuItem(value: 'de', child: Text('German')),
                  DropdownMenuItem(value: 'it', child: Text('Italian')),
                  DropdownMenuItem(value: 'pt', child: Text('Portuguese')),
                  DropdownMenuItem(value: 'ja', child: Text('Japanese')),
                  DropdownMenuItem(value: 'ko', child: Text('Korean')),
                  DropdownMenuItem(value: 'zh', child: Text('Chinese')),
                ],
                onChanged: (value) {
                  setState(() {
                    _selectedLanguage = value;
                  });
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _isSaving ? null : _saveSentence,
          child: _isSaving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Save'),
        ),
      ],
    );
  }
}
