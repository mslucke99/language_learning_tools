import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/llm_service.dart';
import '../services/settings_service.dart';

class LLMProviderSettingsScreen extends StatefulWidget {
  const LLMProviderSettingsScreen({super.key});

  @override
  State<LLMProviderSettingsScreen> createState() =>
      _LLMProviderSettingsScreenState();
}

class _LLMProviderSettingsScreenState extends State<LLMProviderSettingsScreen> {
  final TextEditingController _geminiKeyController = TextEditingController();
  final TextEditingController _openaiKeyController = TextEditingController();
  final TextEditingController _openaiUrlController = TextEditingController(
    text: 'https://api.openai.com/v1',
  );

  @override
  void dispose() {
    _geminiKeyController.dispose();
    _openaiKeyController.dispose();
    _openaiUrlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final llmService = Provider.of<LLMService>(context);
    final settingsService = Provider.of<SettingsService>(context);
    final currentProvider = llmService.selectedProviderType;

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Provider Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Active Provider',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  RadioListTile<String>(
                    title: const Text('Google Gemini'),
                    value: 'gemini',
                    groupValue: currentProvider,
                    onChanged: (value) => llmService.setProvider(value!),
                  ),
                  RadioListTile<String>(
                    title: const Text('OpenAI / Generic OpenAI'),
                    value: 'openai',
                    groupValue: currentProvider,
                    onChanged: (value) => llmService.setProvider(value!),
                  ),
                  RadioListTile<String>(
                    title: const Text('Ollama (Local)'),
                    value: 'ollama',
                    groupValue: currentProvider,
                    onChanged: (value) => llmService.setProvider(value!),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Configuration',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (currentProvider != 'ollama')
                      TextField(
                        controller: currentProvider == 'gemini'
                            ? _geminiKeyController
                            : _openaiKeyController,
                        decoration: const InputDecoration(
                          labelText: 'API Key',
                          border: OutlineInputBorder(),
                        ),
                        obscureText: true,
                      ),
                    if (currentProvider != 'gemini') ...[
                      const SizedBox(height: 16),
                      TextField(
                        controller: _openaiUrlController,
                        decoration: const InputDecoration(
                          labelText: 'Base URL',
                          border: OutlineInputBorder(),
                          hintText: 'https://api.openai.com/v1',
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    const Text(
                      'Model Name',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        hintText: 'e.g. gemini-1.5-flash, gpt-4o, llama3',
                      ),
                      onChanged: (val) {
                        // We'll update the model in the provider
                        llmService.updateProviderConfig(
                          currentProvider,
                          model: val,
                        );
                      },
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Request Timeout (seconds)',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      initialValue: settingsService.requestTimeout.toString(),
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (val) {
                        final timeout = int.tryParse(val);
                        if (timeout != null)
                          settingsService.setRequestTimeout(timeout);
                      },
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: () async {
                        await llmService.updateProviderConfig(
                          currentProvider,
                          key: (currentProvider == 'gemini')
                              ? _geminiKeyController.text
                              : _openaiKeyController.text,
                          url: _openaiUrlController.text,
                        );
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Configuration saved'),
                            ),
                          );
                        }
                      },
                      child: const Text('Apply Changes'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () async {
                final result = await llmService.generate("Ping");
                if (mounted) {
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text("Test Connection"),
                      content: Text(
                        result != null
                            ? "Success! response received."
                            : "Failed to connect.",
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text("OK"),
                        ),
                      ],
                    ),
                  );
                }
              },
              icon: const Icon(Icons.bolt),
              label: const Text('Test Connection'),
            ),
          ],
        ),
      ),
    );
  }
}
