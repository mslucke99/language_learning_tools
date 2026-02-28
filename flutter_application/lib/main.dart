import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:io';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'screens/data_browser_home_screen.dart';
import 'screens/sync_settings_screen.dart';
import 'screens/llm_provider_settings_screen.dart';
import 'screens/settings_home_screen.dart';
import 'screens/language_settings_screen.dart';
import 'screens/prompt_editor_screen.dart';
import 'services/llm_service.dart';
import 'services/settings_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (Platform.isWindows || Platform.isLinux) {
    // Initialize FFI
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }

  final llmService = LLMService();
  final settingsService = SettingsService();

  await llmService.initialize();
  await settingsService.initialize();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: llmService),
        ChangeNotifierProvider.value(value: settingsService),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Proficiency Suites',
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
        '/settings': (context) => const SettingsHomeScreen(),
        '/sync': (context) => const SyncSettingsScreen(),
        '/llm_settings': (context) => const LLMProviderSettingsScreen(),
        '/languages': (context) => const LanguageSettingsScreen(),
        '/prompts': (context) => const PromptEditorScreen(),
      },
    );
  }
}
