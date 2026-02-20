import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/settings_service.dart';
import '../services/prompts.dart';

class PromptEditorScreen extends StatefulWidget {
  const PromptEditorScreen({super.key});

  @override
  State<PromptEditorScreen> createState() => _PromptEditorScreenState();
}

class _PromptEditorScreenState extends State<PromptEditorScreen> {
  String? _selectedCategory;
  String? _selectedPromptId;
  String? _selectedTemplateType;
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final settingsService = Provider.of<SettingsService>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Prompt Editor'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (_selectedPromptId != null)
            IconButton(
              icon: const Icon(Icons.save),
              onPressed: () async {
                await settingsService.setCustomPrompt(
                  _selectedCategory!,
                  _selectedPromptId!,
                  _selectedTemplateType!,
                  _controller.text,
                );
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Prompt template saved')),
                  );
                }
              },
            ),
        ],
      ),
      body: Row(
        children: [
          // Sidebar
          SizedBox(
            width: 250,
            child: ListView(
              children: [
                _buildCategory(
                  context,
                  'word',
                  'Words (Definitions, Examples)',
                ),
                _buildCategory(
                  context,
                  'sentence',
                  'Sentences (Grammar, Context)',
                ),
                _buildCategory(context, 'writing', 'Writing Lab'),
                _buildCategory(context, 'chat', 'AI Chat Tutor'),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          // Editor
          Expanded(
            child: _selectedPromptId == null
                ? const Center(child: Text('Select a prompt to edit'))
                : Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Editing: $_selectedPromptId ($_selectedTemplateType)',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 16),
                        Expanded(
                          child: TextField(
                            controller: _controller,
                            maxLines: null,
                            expands: true,
                            textAlignVertical: TextAlignVertical.top,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 13,
                            ),
                            decoration: const InputDecoration(
                              border: OutlineInputBorder(),
                              hintText: 'Enter template body...',
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            ElevatedButton(
                              onPressed: () async {
                                await settingsService.resetPrompt(
                                  _selectedCategory!,
                                  _selectedPromptId!,
                                  _selectedTemplateType!,
                                );
                                _loadPrompt(settingsService);
                              },
                              child: const Text('Restore Default'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategory(BuildContext context, String catId, String title) {
    final prompts = _getPromptsForCategory(catId);
    return ExpansionTile(
      title: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
      ),
      initiallyExpanded: true,
      children: prompts.keys.map((pid) {
        final pinfo = prompts[pid]!;
        if (pinfo.containsKey('native') && pinfo.containsKey('study')) {
          return ExpansionTile(
            title: Padding(
              padding: const EdgeInsets.only(left: 16.0),
              child: Text(pinfo['name'] ?? pid),
            ),
            children: [
              _buildPromptItem(catId, pid, 'native', 'Native Template'),
              _buildPromptItem(catId, pid, 'study', 'Study Template'),
            ],
          );
        } else {
          return _buildPromptItem(catId, pid, 'template', pinfo['name'] ?? pid);
        }
      }).toList(),
    );
  }

  Widget _buildPromptItem(
    String catId,
    String pid,
    String type,
    String display,
  ) {
    final isSelected =
        _selectedCategory == catId &&
        _selectedPromptId == pid &&
        _selectedTemplateType == type;
    return ListTile(
      contentPadding: const EdgeInsets.only(left: 32.0),
      title: Text(
        display,
        style: TextStyle(
          color: isSelected ? Theme.of(context).colorScheme.primary : null,
        ),
      ),
      onTap: () {
        setState(() {
          _selectedCategory = catId;
          _selectedPromptId = pid;
          _selectedTemplateType = type;
        });
        _loadPrompt(Provider.of<SettingsService>(context, listen: false));
      },
    );
  }

  Map<String, Map<String, String>> _getPromptsForCategory(String catId) {
    switch (catId) {
      case 'word':
        return Prompts.wordPrompts;
      case 'sentence':
        return Prompts.sentencePrompts;
      case 'writing':
        return Prompts.writingPrompts;
      case 'chat':
        return Prompts.chatPrompts;
      default:
        return {};
    }
  }

  Future<void> _loadPrompt(SettingsService settingsService) async {
    final custom = await settingsService.getCustomPrompt(
      _selectedCategory!,
      _selectedPromptId!,
      _selectedTemplateType!,
    );
    if (custom != null) {
      _controller.text = custom;
    } else {
      final prompts = _getPromptsForCategory(_selectedCategory!);
      final entry = prompts[_selectedPromptId!]!;
      _controller.text = entry[_selectedTemplateType!] ?? '';
    }
  }
}
