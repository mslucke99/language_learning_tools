import 'package:flutter/material.dart';
import 'package:proficiency_suites/services/deck_service.dart';

class DeckEditorScreen extends StatefulWidget {
  final int? deckId; // null for new deck
  final String? initialName;
  final String? initialDescription;
  final String? initialLanguage;

  const DeckEditorScreen({
    super.key,
    this.deckId,
    this.initialName,
    this.initialDescription,
    this.initialLanguage,
  });

  @override
  State<DeckEditorScreen> createState() => _DeckEditorScreenState();
}

class _DeckEditorScreenState extends State<DeckEditorScreen> {
  final DeckService _deckService = DeckService();
  final _formKey = GlobalKey<FormState>();
  
  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  String? _selectedLanguage;
  
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialName);
    _descriptionController = TextEditingController(text: widget.initialDescription);
    _selectedLanguage = widget.initialLanguage;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _saveDeck() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isSaving = true);
    
    try {
      if (widget.deckId == null) {
        // Create new deck
        final deckId = await _deckService.createDeck(
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim(),
          language: _selectedLanguage,
        );
        
        if (mounted) {
          Navigator.pop(context, deckId);
        }
      } else {
        // Update existing deck
        await _deckService.updateDeck(
          widget.deckId!,
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim(),
          language: _selectedLanguage,
        );
        
        if (mounted) {
          Navigator.pop(context, true);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving deck: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isNewDeck = widget.deckId == null;
    
    return Scaffold(
      appBar: AppBar(
        title: Text(isNewDeck ? 'New Deck' : 'Edit Deck'),
        actions: [
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
              onPressed: _saveDeck,
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Deck Name',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.style),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Please enter a deck name';
                }
                return null;
              },
              enabled: !_isSaving,
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (optional)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.description),
              ),
              maxLines: 3,
              enabled: !_isSaving,
            ),
            const SizedBox(height: 16),
            
            DropdownButtonFormField<String>(
              value: _selectedLanguage,
              decoration: const InputDecoration(
                labelText: 'Language (optional)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.language),
              ),
              items: const [
                DropdownMenuItem(value: null, child: Text('None')),
                DropdownMenuItem(value: 'Korean', child: Text('Korean')),
                DropdownMenuItem(value: 'Japanese', child: Text('Japanese')),
                DropdownMenuItem(value: 'Chinese', child: Text('Chinese')),
                DropdownMenuItem(value: 'Spanish', child: Text('Spanish')),
                DropdownMenuItem(value: 'French', child: Text('French')),
                DropdownMenuItem(value: 'German', child: Text('German')),
                DropdownMenuItem(value: 'Italian', child: Text('Italian')),
                DropdownMenuItem(value: 'Portuguese', child: Text('Portuguese')),
                DropdownMenuItem(value: 'Russian', child: Text('Russian')),
                DropdownMenuItem(value: 'Arabic', child: Text('Arabic')),
              ],
              onChanged: _isSaving ? null : (value) {
                setState(() => _selectedLanguage = value);
              },
            ),
            const SizedBox(height: 24),
            
            ElevatedButton.icon(
              onPressed: _isSaving ? null : _saveDeck,
              icon: const Icon(Icons.save),
              label: Text(isNewDeck ? 'Create Deck' : 'Save Changes'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
