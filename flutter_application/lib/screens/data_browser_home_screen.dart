import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:io' show Platform;
import '../services/settings_service.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'deck_list_screen.dart';
import 'collection_list_screen.dart';
import 'import_list_screen.dart';
import 'grammar_book_screen.dart';
import 'writing_session_list_screen.dart';
import 'chat_session_list_screen.dart';
import 'active_chat_screen.dart';
import 'roleplay_scenario_list_screen.dart';
import 'known_words_screen.dart';
import 'sentence_mining_screen.dart';
import 'statistics_dashboard_screen.dart';
import 'writing_lab_screen.dart';
import 'exam_setup_screen.dart';
import '../services/ad_service.dart';

class DataBrowserHomeScreen extends StatelessWidget {
  const DataBrowserHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final settingsService = Provider.of<SettingsService>(context);
    final studyLang = settingsService.studyLanguage;
    
    // Check if running on a mobile platform
    final bool isMobile = Platform.isAndroid || Platform.isIOS;

    return Consumer<AdService>(
      builder: (context, adService, child) {
        // Build main content with all features
        final Widget mainContent = SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSectionHeader(context, 'Study ($studyLang)', Icons.school),
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
                title: 'Active Chat',
                subtitle: 'Practice conversation with AI tutor',
                icon: Icons.chat_bubble,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ActiveChatScreen(),
                  ),
                ),
              ),
              _buildCategoryCard(
                context,
                title: 'Roleplay',
                subtitle: 'Practice real-world scenarios',
                icon: Icons.theater_comedy,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const RoleplayScenarioListScreen(),
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
              _buildCategoryCard(
                context,
                title: 'Known Words',
                subtitle: 'Your vocabulary database',
                icon: Icons.library_books,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => KnownWordsScreen(language: studyLang),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              _buildSectionHeader(context, 'Knowledge Base', Icons.menu_book),
              _buildCategoryCard(
                context,
                title: 'Imported Words',
                subtitle: 'Words saved from the web',
                icon: Icons.text_fields,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ImportListScreen(contentType: 'word'),
                  ),
                ),
              ),
              _buildCategoryCard(
                context,
                title: 'Imported Sentences',
                subtitle: 'Sentences saved from the web',
                icon: Icons.format_quote,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ImportListScreen(contentType: 'sentence'),
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
              _buildCategoryCard(
                context,
                title: 'Sentence Mining',
                subtitle: 'Find target sentences for study',
                icon: Icons.travel_explore,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) =>
                        SentenceMiningScreen(language: studyLang),
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
              _buildCategoryCard(
                context,
                title: 'Writing Lab',
                subtitle: 'Improve your writing with feedback',
                icon: Icons.edit_document,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const WritingLabScreen(),
                  ),
                ),
              ),
              _buildCategoryCard(
                context,
                title: 'Statistics',
                subtitle: 'Track your learning progress',
                icon: Icons.bar_chart,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const StatisticsDashboardScreen(),
                  ),
                ),
              ),
              _buildCategoryCard(
                context,
                title: 'Exam Practice',
                subtitle: 'Test your knowledge',
                icon: Icons.assignment,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ExamSetupScreen(language: studyLang),
                  ),
                ),
              ),
            ],
          ),
        );

        // Build ad widget only on mobile platforms
        Widget? adWidget;
        if (isMobile && adService.showAd && adService.bannerAd != null) {
          adWidget = SizedBox(
            width: adService.bannerAd!.size.width.toDouble(),
            height: adService.bannerAd!.size.height.toDouble(),
            child: AdWidget(ad: adService.bannerAd!),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('Proficiency Suites'),
            backgroundColor: Theme.of(context).colorScheme.inversePrimary,
            actions: [
              IconButton(
                icon: const Icon(Icons.settings),
                tooltip: 'Settings',
                onPressed: () {
                  Navigator.pushNamed(context, '/settings');
                },
              ),
            ],
          ),
          body: Column(
            children: [
              if (isMobile && adWidget != null && adService.placement == AdPlacement.top)
                adWidget,
              Expanded(child: mainContent),
              if (isMobile && adWidget != null && adService.placement == AdPlacement.bottom)
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
