import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/settings_service.dart';

class LanguageSettingsScreen extends StatelessWidget {
  const LanguageSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final settingsService = Provider.of<SettingsService>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Language Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          const Text(
            'Study Language (Target)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: settingsService.studyLanguage,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'Select Language',
            ),
            items: const [
              DropdownMenuItem(value: 'Spanish', child: Text('Spanish')),
              DropdownMenuItem(value: 'French', child: Text('French')),
              DropdownMenuItem(value: 'German', child: Text('German')),
              DropdownMenuItem(value: 'Japanese', child: Text('Japanese')),
              DropdownMenuItem(value: 'Korean', child: Text('Korean')),
              DropdownMenuItem(value: 'Mandarin', child: Text('Mandarin')),
              DropdownMenuItem(value: 'Italian', child: Text('Italian')),
              DropdownMenuItem(value: 'Portuguese', child: Text('Portuguese')),
              DropdownMenuItem(value: 'Russian', child: Text('Russian')),
              DropdownMenuItem(value: 'Arabic', child: Text('Arabic')),
              DropdownMenuItem(
                value: 'Biblical Greek',
                child: Text('Biblical Greek'),
              ),
            ],
            onChanged: (val) {
              if (val != null) settingsService.setStudyLanguage(val);
            },
          ),
          const SizedBox(height: 24),
          const Text(
            'Native Language (UI & Definitions)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: settingsService.nativeLanguage,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'e.g. English',
            ),
            onChanged: (val) {
              settingsService.setNativeLanguage(val);
            },
          ),
          const SizedBox(height: 32),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.tips_and_updates, color: Colors.amber),
                      SizedBox(width: 8),
                      Text(
                        'Tip',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  Text(
                    'The study language is what you are learning. Native language is used for AI-generated definitions and the application interface where available.',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
