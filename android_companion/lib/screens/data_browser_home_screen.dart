import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'deck_list_screen.dart';
import 'collection_list_screen.dart';
import 'import_list_screen.dart';
import 'grammar_book_screen.dart';
import 'writing_session_list_screen.dart';
import 'chat_session_list_screen.dart';
import '../services/ad_service.dart';

class DataBrowserHomeScreen extends StatelessWidget {
  const DataBrowserHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AdService>(
      builder: (context, adService, child) {
        final Widget mainContent = SingleChildScrollView(
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
                  MaterialPageRoute(
                    builder: (context) => const DeckListScreen(),
                  ),
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
        );

        // Build ad widget if loaded
        Widget? adWidget;
        if (adService.showAd && adService.bannerAd != null) {
          adWidget = SizedBox(
            width: adService.bannerAd!.size.width.toDouble(),
            height: adService.bannerAd!.size.height.toDouble(),
            child: AdWidget(ad: adService.bannerAd!),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('Brain Browser'),
            backgroundColor: Theme.of(context).colorScheme.inversePrimary,
            actions: [
              IconButton(
                icon: const Icon(Icons.sync),
                tooltip: 'Sync Settings',
                onPressed: () {
                  Navigator.pushNamed(context, '/sync');
                },
              ),
              PopupMenuButton<String>(
                icon: const Icon(Icons.settings),
                tooltip: 'Settings',
                onSelected: (value) {
                  if (value == 'llm') {
                    Navigator.pushNamed(context, '/llm_settings');
                  } else if (value == 'ads') {
                    Navigator.pushNamed(context, '/ad_settings');
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'llm',
                    child: ListTile(
                      leading: Icon(Icons.smart_toy),
                      title: Text('LLM Settings'),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'ads',
                    child: ListTile(
                      leading: Icon(Icons.monetization_on),
                      title: Text('Ad Settings'),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                ],
              ),
            ],
          ),
          body: Column(
            children: [
              if (adWidget != null && adService.placement == AdPlacement.top)
                adWidget,
              Expanded(child: mainContent),
              if (adWidget != null && adService.placement == AdPlacement.bottom)
                adWidget,
            ],
          ),
        );
      },
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
