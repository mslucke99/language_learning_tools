/// Word Entry Dialog
/// 
/// Allows users to manually add words to their vocabulary list.
/// Words are saved to imported_content with content_type='word'.

import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class WordEntryDialog extends StatefulWidget {
  final String? initialLanguage;
  
  const WordEntryDialog({super.key, this.initialLanguage});
  
  @override
  State<WordEntryDialog> createState() => _WordEntryDialogState();
}

class _WordEntryDialogState extends State<WordEntryDialog> {
  final _formKey = GlobalKey<FormState>();
  final _wordController = TextEditingController();
  final _contextController = TextEditingController();
  final _urlController = TextEditingController();
  String? _selectedLanguage;
  bool _isSaving = false;
  
  final DatabaseHelper _dbHelper = DatabaseHelper();
  
  @override
  void initState() {
    super.initState();
    _selectedLanguage = widget.initialLanguage ?? 'es'; // Default to Spanish
  }
  
  @override
  void dispose() {
    _wordController.dispose();
    _contextController.dispose();
    _urlController.dispose();
    super.dispose();
  }
  
  Future<int?> _saveWord() async {
    if (!_formKey.currentState!.validate()) {
      return null;
    }
    
    setState(() {
      _isSaving = true;
    });
    
    try {
      final now = DateTime.now().toIso8601String();
      final wordId = await _dbHelper.insertItem('imported_content', {
        'content_type': 'word',
        'content': _wordController.text.trim(),
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
        Navigator.pop(context, wordId);
      }
      
      return wordId;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving word: $e'),
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
      title: const Text('Add Word'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _wordController,
                decoration: const InputDecoration(
                  labelText: 'Word *',
                  hintText: 'Enter word to study',
                  border: OutlineInputBorder(),
                ),
                autofocus: true,
                textCapitalization: TextCapitalization.none,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Word is required';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _contextController,
                decoration: const InputDecoration(
                  labelText: 'Context (optional)',
                  hintText: 'e.g., "from news article"',
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
          onPressed: _isSaving ? null : _saveWord,
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
