import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'services/drive_service.dart';
import 'services/database_helper.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Brain Companion',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const SyncHomePage(title: 'Companion App Sync'),
    );
  }
}

class SyncHomePage extends StatefulWidget {
  const SyncHomePage({super.key, required this.title});

  final String title;

  @override
  State<SyncHomePage> createState() => _SyncHomePageState();
}

class _SyncHomePageState extends State<SyncHomePage> {
  final DriveService _driveService = DriveService();
  final DatabaseHelper _dbHelper = DatabaseHelper();

  GoogleSignInAccount? _currentUser;
  String _statusMessage = "Ready";
  int _cardCount = 0;

  @override
  void initState() {
    super.initState();
    _checkDbStatus();
  }

  Future<void> _checkDbStatus() async {
    final count = await _dbHelper.getFlashcardCount();
    setState(() {
      _cardCount = count;
    });
  }

  Future<void> _handleSignIn() async {
    try {
      final user = await _driveService.signIn();
      setState(() {
        _currentUser = user;
        _statusMessage = user != null
            ? "Signed in as ${user.email}"
            : "Sign in failed";
      });
    } catch (e) {
      setState(() => _statusMessage = "Error: $e");
    }
  }

  Future<void> _handleDownload() async {
    if (_currentUser == null) return;
    setState(() => _statusMessage = "Downloading...");
    try {
      await _driveService.downloadDatabase();
      await _dbHelper.reloadDatabase(); // Key step!
      await _checkDbStatus();
      setState(() => _statusMessage = "Download Complete! DB Reloaded.");
    } catch (e) {
      setState(() => _statusMessage = "Download Failed: $e");
    }
  }

  Future<void> _handleUpload() async {
    if (_currentUser == null) return;
    setState(() => _statusMessage = "Uploading...");
    try {
      await _driveService.uploadDatabase();
      setState(() => _statusMessage = "Upload Complete!");
    } catch (e) {
      setState(() => _statusMessage = "Upload Failed: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(
              'Status: $_statusMessage',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 20),
            Text(
              'Local Flashcards: $_cardCount',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 40),
            if (_currentUser == null)
              ElevatedButton.icon(
                onPressed: _handleSignIn,
                icon: const Icon(Icons.login),
                label: const Text('Sign in with Google'),
              )
            else ...[
              Text('User: ${_currentUser!.email}'),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _handleDownload,
                icon: const Icon(Icons.cloud_download),
                label: const Text('Restore from Cloud'),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _handleUpload,
                icon: const Icon(Icons.cloud_upload),
                label: const Text('Backup to Cloud'),
              ),
              const SizedBox(height: 20),
              OutlinedButton(
                onPressed: () async {
                  await _driveService.signOut();
                  setState(() => _currentUser = null);
                },
                child: const Text('Sign Out'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
