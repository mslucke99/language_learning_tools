import 'package:flutter/material.dart';
import 'screens/data_browser_home_screen.dart';
import 'screens/sync_settings_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Brain Companion',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.teal,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      // Set the Browser Hub as the initial route
      home: const DataBrowserHomeScreen(),
      routes: {'/sync': (context) => const SyncSettingsScreen()},
    );
  }
}
