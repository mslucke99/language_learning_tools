import 'package:flutter/material.dart';

class SettingsHomeScreen extends StatelessWidget {
  const SettingsHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        children: [
          _buildSettingsSection(
            context,
            title: 'AI & Intelligence',
            children: [
              ListTile(
                leading: const Icon(Icons.bolt, color: Colors.amber),
                title: const Text('AI Provider Settings'),
                subtitle: const Text('Configure Gemini or OpenAI API keys'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.pushNamed(context, '/llm_settings'),
              ),
              ListTile(
                leading: const Icon(Icons.psychology, color: Colors.purple),
                title: const Text('AI Prompt Editor'),
                subtitle: const Text('Customize how the AI tutor behaves'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.pushNamed(context, '/prompts'),
              ),
            ],
          ),
          const Divider(),
          _buildSettingsSection(
            context,
            title: 'Application',
            children: [
              ListTile(
                leading: const Icon(Icons.language, color: Colors.green),
                title: const Text('Language Settings'),
                subtitle: const Text('Configure Study and Native languages'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.pushNamed(context, '/languages'),
              ),
              ListTile(
                leading: const Icon(Icons.sync, color: Colors.blue),
                title: const Text('Synchronization'),
                subtitle: const Text(
                  'Configure cloud sync and database settings',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.pushNamed(context, '/sync'),
              ),
            ],
          ),
          const Divider(),
          _buildSettingsSection(
            context,
            title: 'About',
            children: [
              const ListTile(
                leading: Icon(Icons.info_outline),
                title: Text('App Version'),
                subtitle: Text('1.0.0'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsSection(
    BuildContext context, {
    required String title,
    required List<Widget> children,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        ...children,
      ],
    );
  }
}
