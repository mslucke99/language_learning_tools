import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/llm_service.dart';

class LLMSettingsPage extends StatefulWidget {
  const LLMSettingsPage({super.key});

  @override
  State<LLMSettingsPage> createState() => _LLMSettingsPageState();
}

class _LLMSettingsPageState extends State<LLMSettingsPage> {
  final _geminiKeyController = TextEditingController();
  final _openaiKeyController = TextEditingController();
  final _openaiUrlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    // This is a bit redundant since LLMService already has them in storage,
    // but the UI controllers need initial values.
    // In a real app, we might get these from a secure storage helper.
  }

  @override
  Widget build(BuildContext context) {
    final llmService = Provider.of<LLMService>(context);

    return Scaffold(
      appBar: AppBar(title: const Text("AI Provider Settings")),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          const Text(
            "Select Provider",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          DropdownButton<String>(
            value: llmService.selectedProviderType,
            isExpanded: true,
            items: const [
              DropdownMenuItem(value: 'gemini', child: Text("Google Gemini")),
              DropdownMenuItem(
                value: 'openai',
                child: Text("OpenAI / Compatible"),
              ),
            ],
            onChanged: (val) {
              if (val != null) llmService.setProvider(val);
            },
          ),
          const SizedBox(height: 24),

          if (llmService.selectedProviderType == 'gemini') ...[
            const Text("Gemini API Key"),
            TextField(
              controller: _geminiKeyController,
              decoration: const InputDecoration(hintText: "Enter API Key"),
              obscureText: true,
            ),
            ElevatedButton(
              onPressed: () {
                llmService.updateGeminiKey(_geminiKeyController.text);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Gemini Key Updated")),
                );
              },
              child: const Text("Apply Gemini Key"),
            ),
          ],

          if (llmService.selectedProviderType == 'openai') ...[
            const Text("OpenAI API Key"),
            TextField(
              controller: _openaiKeyController,
              decoration: const InputDecoration(hintText: "Enter API Key"),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            const Text("Base URL"),
            TextField(
              controller: _openaiUrlController,
              decoration: const InputDecoration(
                hintText: "https://api.openai.com/v1",
              ),
            ),
            ElevatedButton(
              onPressed: () {
                llmService.updateOpenAIConfig(
                  _openaiKeyController.text,
                  _openaiUrlController.text,
                );
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("OpenAI Config Updated")),
                );
              },
              child: const Text("Apply OpenAI Config"),
            ),
          ],

          const SizedBox(height: 48),
          const Divider(),
          ListTile(
            title: const Text("Test Provider"),
            subtitle: Text(
              "Current: ${llmService.currentProvider?.providerName ?? 'Not Configured'}",
            ),
            trailing: const Icon(Icons.bolt),
            onTap: () async {
              final result = await llmService.generate(
                "Hello, are you working?",
              );
              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text("Test Result"),
                  content: Text(result ?? "No response received."),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text("OK"),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
