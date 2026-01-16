import 'package:flutter/material.dart';
import 'deck_list_screen.dart';
import 'collection_list_screen.dart';
import 'import_list_screen.dart';
import 'grammar_book_screen.dart';
import 'writing_session_list_screen.dart';
import 'chat_session_list_screen.dart';
// Future imports for other screens
// import 'collection_list_screen.dart';
// import 'import_list_screen.dart';
// import 'session_list_screen.dart';

class DataBrowserHomeScreen extends StatelessWidget {
  const DataBrowserHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Brain Browser'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: 'Sync Settings',
            onPressed: () {
              // This will be navigated to the refactored SyncSettingsScreen
              Navigator.pushNamed(context, '/sync');
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(context, 'Study', Icons.school),
            _buildCategoryCard(
              context,
              title: 'Decks & Flashcards',
              subtitle: 'Browse your spaced-repetition cards',
              icon: Icons.style,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const DeckListScreen()),
              ),
            ),
            _buildCategoryCard(
              context,
              title: 'Collections',
              subtitle: 'Organize items by topic or source',
              icon: Icons.folder_copy,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const CollectionListScreen(),
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader(context, 'Knowledge Base', Icons.menu_book),
            _buildCategoryCard(
              context,
              title: 'Imports',
              subtitle: 'Words and sentences from the web',
              icon: Icons.extension,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const ImportListScreen(),
                ),
              ),
            ),
            _buildCategoryCard(
              context,
              title: 'Grammar Book',
              subtitle: 'Saved rules and explanations',
              icon: Icons.history_edu,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const GrammarBookScreen(),
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildSectionHeader(context, 'Activity', Icons.history),
            _buildCategoryCard(
              context,
              title: 'Writing Sessions',
              subtitle: 'Feedback on your compositions',
              icon: Icons.edit_note,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const WritingSessionListScreen(),
                ),
              ),
            ),
            _buildCategoryCard(
              context,
              title: 'Chat History',
              subtitle: 'Past conversations with your AI tutor',
              icon: Icons.chat,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const ChatSessionListScreen(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(
    BuildContext context,
    String title,
    IconData icon,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.teal),
          const SizedBox(width: 8),
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Colors.teal.shade800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryCard(
    BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 6.0),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.teal.shade50,
          child: Icon(icon, color: Colors.teal),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right, size: 20),
        onTap: onTap,
      ),
    );
  }
}
