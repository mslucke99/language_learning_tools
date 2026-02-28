import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../services/firebase_service.dart';
import '../services/database_helper.dart';

class SyncSettingsScreen extends StatefulWidget {
  const SyncSettingsScreen({super.key});

  @override
  State<SyncSettingsScreen> createState() => _SyncSettingsScreenState();
}

class _SyncSettingsScreenState extends State<SyncSettingsScreen> {
  final FirebaseService _firebaseService = FirebaseService();
  final DatabaseHelper _dbHelper = DatabaseHelper();

  String _statusMessage = "Ready";
  bool _isSyncing = false;
  int _cardCount = 0;

  @override
  void initState() {
    super.initState();
    _checkDbStatus();
  }

  Future<void> _checkDbStatus() async {
    final count = await _dbHelper.getFlashcardCount();
    if (mounted) setState(() => _cardCount = count);
  }

  Future<void> _handleSignIn() async {
    final user = await _firebaseService.signInWithGoogle();
    if (user != null) {
      if (mounted)
        setState(() => _statusMessage = "Signed in as ${user.email}");
    } else {
      if (mounted)
        setState(() => _statusMessage = "Sign In Failed or Cancelled");
    }
  }

  Future<void> _handleSignOut() async {
    await _firebaseService.signOut();
    if (mounted) setState(() => _statusMessage = "Signed Out");
  }

  Future<void> _handleSync() async {
    if (_firebaseService.currentUser == null) {
      setState(() => _statusMessage = "Please sign in to sync.");
      return;
    }

    setState(() {
      _isSyncing = true;
      _statusMessage = "Syncing with Firestore...";
    });

    try {
      final stats = await _firebaseService.sync();
      await _checkDbStatus();
      if (mounted) {
        setState(() {
          _statusMessage =
              "Sync Complete!\nDownloaded: ${stats['downloaded']}, Uploaded: ${stats['uploaded']}";
        });
      }
    } catch (e) {
      if (mounted) setState(() => _statusMessage = "Sync Error: $e");
    } finally {
      if (mounted) setState(() => _isSyncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sync Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: StreamBuilder<User?>(
        stream: _firebaseService.authStateChanges,
        builder: (context, snapshot) {
          final user = snapshot.data;
          final isSignedIn = user != null;

          return Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  Icon(
                    isSignedIn ? Icons.cloud_done : Icons.cloud_off,
                    size: 64,
                    color: isSignedIn ? Colors.teal : Colors.grey,
                  ),
                  const SizedBox(height: 20),
                  Text(
                    _statusMessage,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 10),
                  if (isSignedIn)
                    Text(
                      "User: ${user.email}",
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  const SizedBox(height: 20),
                  Text(
                    'Local Flashcards: $_cardCount',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 40),

                  if (!isSignedIn)
                    ElevatedButton.icon(
                      onPressed: _handleSignIn,
                      icon: const Icon(Icons.login),
                      label: const Text('Sign In with Google'),
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size(200, 50),
                      ),
                    )
                  else ...[
                    ElevatedButton.icon(
                      onPressed: _isSyncing ? null : _handleSync,
                      icon: _isSyncing
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.sync),
                      label: const Text('Sync Now'),
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size(200, 50),
                        backgroundColor: Colors.teal.shade50,
                      ),
                    ),
                    const SizedBox(height: 20),
                    TextButton.icon(
                      onPressed: _handleSignOut,
                      icon: const Icon(Icons.logout),
                      label: const Text('Sign Out'),
                      style: TextButton.styleFrom(foregroundColor: Colors.red),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
