/// Grammar Follow-up Dialog
/// 
/// Allows users to ask follow-up questions about sentence explanations.

import 'package:flutter/material.dart';

class GrammarFollowupDialog extends StatefulWidget {
  const GrammarFollowupDialog({super.key});
  
  @override
  State<GrammarFollowupDialog> createState() => _GrammarFollowupDialogState();
}

class _GrammarFollowupDialogState extends State<GrammarFollowupDialog> {
  final _formKey = GlobalKey<FormState>();
  final _questionController = TextEditingController();
  
  @override
  void dispose() {
    _questionController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Ask Question'),
      content: Form(
        key: _formKey,
        child: TextFormField(
          controller: _questionController,
          decoration: const InputDecoration(
            labelText: 'Your Question',
            hintText: 'e.g., Why is this verb in that tense?',
            border: OutlineInputBorder(),
          ),
          maxLines: 3,
          autofocus: true,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return 'Question is required';
            }
            return null;
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.pop(context, _questionController.text.trim());
            }
          },
          child: const Text('Ask'),
        ),
      ],
    );
  }
}
