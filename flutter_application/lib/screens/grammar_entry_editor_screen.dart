import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../services/grammar_service.dart';
import '../services/collection_service.dart';
import '../services/llm_service.dart';

class GrammarEntryEditorScreen extends StatefulWidget {
  final GrammarBookEntry? entry;
  final String? language;

  const GrammarEntryEditorScreen({super.key, this.entry, this.language});

  @override
  State<GrammarEntryEditorScreen> createState() =>
      _GrammarEntryEditorScreenState();
}

class _GrammarEntryEditorScreenState extends State<GrammarEntryEditorScreen> {
  late GrammarService _grammarService;
  final CollectionService _collectionService = CollectionService();

  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _contentController = TextEditingController();
  final TextEditingController _tagsController = TextEditingController();

  int _proficiency = 0;
  int? _collectionId;
  List<Collection> _collections = [];
  bool _isLoading = false;
  bool _showPreview = false;

  @override
  void initState() {
    super.initState();
    final llmService = Provider.of<LLMService>(context, listen: false);
    _grammarService = GrammarService(llmService);
    _loadCollections();

    if (widget.entry != null) {
      _loadEntry();
    }
  }

  void _loadEntry() {
    final entry = widget.entry!;
    _titleController.text = entry.title;
    _contentController.text = entry.content;
    _tagsController.text = entry.tags ?? '';
    _proficiency = entry.proficiency ?? 0;
    _collectionId = entry.collectionId;
  }

  Future<void> _loadCollections() async {
    final collections = await _collectionService.getCollections(
      type: 'grammar',
    );
    setState(() => _collections = collections);
  }

  Future<void> _save() async {
    if (_titleController.text.trim().isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Title is required')));
      return;
    }

    setState(() => _isLoading = true);

    try {
      if (widget.entry == null) {
        await _grammarService.createEntry(
          title: _titleController.text,
          content: _contentController.text,
          language: widget.language,
          tags: _tagsController.text.isEmpty ? null : _tagsController.text,
          proficiency: _proficiency,
          collectionId: _collectionId,
        );
      } else {
        await _grammarService.updateEntry(
          widget.entry!.id!,
          title: _titleController.text,
          content: _contentController.text,
          tags: _tagsController.text.isEmpty ? null : _tagsController.text,
          proficiency: _proficiency,
          collectionId: _collectionId,
        );
      }

      if (mounted) {
        Navigator.pop(context, true);
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.entry == null ? 'New Grammar Entry' : 'Edit Entry'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: Icon(_showPreview ? Icons.edit : Icons.preview),
            onPressed: () => setState(() => _showPreview = !_showPreview),
            tooltip: _showPreview ? 'Edit' : 'Preview',
          ),
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _isLoading ? null : _save,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: _showPreview ? _buildPreview() : _buildEditor(),
            ),
    );
  }

  Widget _buildEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _titleController,
          decoration: const InputDecoration(
            labelText: 'Title',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _contentController,
          decoration: const InputDecoration(
            labelText: 'Content',
            border: OutlineInputBorder(),
            alignLabelWithHint: true,
          ),
          maxLines: 15,
          minLines: 10,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _tagsController,
          decoration: const InputDecoration(
            labelText: 'Tags (comma-separated)',
            border: OutlineInputBorder(),
            hintText: 'grammar, verb, conjugation',
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Proficiency Level: ${_getProficiencyLabel(_proficiency)}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Slider(
                  value: _proficiency.toDouble(),
                  min: 0,
                  max: 5,
                  divisions: 5,
                  label: _getProficiencyLabel(_proficiency),
                  onChanged: (value) =>
                      setState(() => _proficiency = value.toInt()),
                ),
                Text(
                  _getProficiencyDescription(_proficiency),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<int?>(
          value: _collectionId,
          decoration: const InputDecoration(
            labelText: 'Collection (Optional)',
            border: OutlineInputBorder(),
          ),
          items: [
            const DropdownMenuItem(value: null, child: Text('None')),
            ..._collections.map(
              (c) => DropdownMenuItem(value: c.id, child: Text(c.name)),
            ),
          ],
          onChanged: (value) => setState(() => _collectionId = value),
        ),
      ],
    );
  }

  Widget _buildPreview() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _titleController.text.isEmpty
                  ? 'Untitled'
                  : _titleController.text,
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (_tagsController.text.isNotEmpty)
              Wrap(
                spacing: 8,
                children: _tagsController.text
                    .split(',')
                    .map(
                      (tag) => Chip(
                        label: Text(tag.trim()),
                        backgroundColor: Colors.teal.shade100,
                      ),
                    )
                    .toList(),
              ),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  Icons.signal_cellular_alt,
                  size: 16,
                  color: Colors.grey.shade600,
                ),
                const SizedBox(width: 4),
                Text(
                  _getProficiencyLabel(_proficiency),
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ],
            ),
            const Divider(height: 24),
            Text(
              _contentController.text.isEmpty
                  ? 'No content'
                  : _contentController.text,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }

  String _getProficiencyLabel(int level) {
    switch (level) {
      case 0:
        return 'Not Learned';
      case 1:
        return 'Beginner';
      case 2:
        return 'Elementary';
      case 3:
        return 'Intermediate';
      case 4:
        return 'Advanced';
      case 5:
        return 'Mastered';
      default:
        return 'Unknown';
    }
  }

  String _getProficiencyDescription(int level) {
    switch (level) {
      case 0:
        return 'Not yet learned';
      case 1:
        return 'Just learned, need practice';
      case 2:
        return 'Can recognize when I see it';
      case 3:
        return 'Can use with some effort';
      case 4:
        return 'Comfortable using it';
      case 5:
        return 'Automatic, no thinking needed';
      default:
        return '';
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    _tagsController.dispose();
    super.dispose();
  }
}
