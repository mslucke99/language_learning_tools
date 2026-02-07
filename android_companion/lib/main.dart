import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/data_browser_home_screen.dart';
import 'screens/sync_settings_screen.dart';
import 'screens/llm_settings_page.dart';
import 'services/llm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final llmService = LLMService();
  await llmService.initialize();

  runApp(
    MultiProvider(
      providers: [ChangeNotifierProvider.value(value: llmService)],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Getcha Fluentia',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.teal,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const DataBrowserHomeScreen(),
      routes: {
        '/sync': (context) => const SyncSettingsScreen(),
        '/llm_settings': (context) => const LLMSettingsPage(),
      },
    );
  }
}
