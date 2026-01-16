import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';
import '../services/dropbox_service.dart';
import '../services/database_helper.dart';
import '../services/sync_merger.dart';
import '../services/conflict_dialog.dart';

class SyncSettingsScreen extends StatefulWidget {
  const SyncSettingsScreen({super.key});

  @override
  State<SyncSettingsScreen> createState() => _SyncSettingsScreenState();
}

class _SyncSettingsScreenState extends State<SyncSettingsScreen> {
  final DropboxService _dropboxService = DropboxService();
  final DatabaseHelper _dbHelper = DatabaseHelper();

  bool _isAuthenticated = false;
  String _statusMessage = "Ready";
  int _cardCount = 0;

  @override
  void initState() {
    super.initState();
    _initDropbox();
    _checkDbStatus();
  }

  Future<void> _initDropbox() async {
    final authed = await _dropboxService.init();
    if (mounted) {
      setState(() {
        _isAuthenticated = authed;
        if (authed) _statusMessage = "Connected to Dropbox";
      });
    }
  }

  Future<void> _checkDbStatus() async {
    final count = await _dbHelper.getFlashcardCount();
    if (mounted) {
      setState(() {
        _cardCount = count;
      });
    }
  }

  Future<void> _handleSignIn() async {
    try {
      await _dropboxService.login();
      if (mounted) {
        setState(() => _statusMessage = "Waiting for authorization...");
      }
    } catch (e) {
      if (mounted) {
        setState(() => _statusMessage = "Error: $e");
      }
    }
  }

  Future<void> _handleDownload() async {
    if (!_dropboxService.isAuthenticated) {
      await _dropboxService.refreshAccessToken();
    }

    if (mounted) setState(() => _statusMessage = "Downloading cloud backup...");
    try {
      final tempPath = await _dropboxService.downloadDatabase();

      if (mounted)
        setState(() => _statusMessage = "Initializing local database...");
      await _dbHelper.initializeSchema();

      if (mounted) setState(() => _statusMessage = "Merging data...");

      final localDb = await _dbHelper.database;
      final remoteDb = await openDatabase(tempPath);

      const lastSyncTime = "1970-01-01T00:00:00";

      final merger = SyncMerger(
        localDb: localDb,
        remoteDb: remoteDb,
        lastSyncTime: lastSyncTime,
      );

      merger.onConflict = (conflict) => showConflictDialog(context, conflict);

      final results = await merger.mergeAll();

      int added = 0;
      int updated = 0;
      int conflicts = 0;
      results.forEach((table, stats) {
        added += stats.$1;
        updated += stats.$2;
        conflicts += stats.$3;
      });

      await remoteDb.close();
      await _dbHelper.reloadDatabase();
      await _checkDbStatus();

      if (mounted) {
        setState(() {
          _statusMessage =
              "Sync Complete!\n"
              "Added: $added, Updated: $updated\n"
              "Conflicts Resolved: $conflicts";
        });
      }
    } catch (e) {
      if (mounted) setState(() => _statusMessage = "Sync Failed: $e");
    }
  }

  Future<void> _handleUpload() async {
    if (mounted) setState(() => _statusMessage = "Uploading backup...");
    try {
      final localPath = await _dbHelper.getDatabasePath();
      await _dropboxService.uploadDatabase(localPath);
      if (mounted) setState(() => _statusMessage = "Upload Complete!");
    } catch (e) {
      if (mounted) setState(() => _statusMessage = "Upload Failed: $e");
    }
  }

  Future<void> _handleCheckpoint() async {
    if (mounted)
      setState(() => _statusMessage = "Creating cloud checkpoint...");
    try {
      final localPath = await _dbHelper.getDatabasePath();
      await _dropboxService.createCloudCheckpoint(localPath);
      if (mounted) {
        setState(
          () =>
              _statusMessage = "Checkpoint Created! (See /checkpoints folder)",
        );
      }
    } catch (e) {
      if (mounted) setState(() => _statusMessage = "Checkpoint Failed: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAuthenticated && _dropboxService.isAuthenticated) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          setState(() {
            _isAuthenticated = true;
            _statusMessage = "Connected to Dropbox ✅";
          });
        }
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sync Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.cloud_sync, size: 64, color: Colors.teal),
              const SizedBox(height: 20),
              Text(
                _statusMessage,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              Text(
                'Local Flashcards: $_cardCount',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 40),
              if (!_isAuthenticated)
                ElevatedButton.icon(
                  onPressed: _handleSignIn,
                  icon: const Icon(Icons.link),
                  label: const Text('Connect Dropbox Account'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(200, 50),
                  ),
                )
              else ...[
                ElevatedButton.icon(
                  onPressed: _handleDownload,
                  icon: const Icon(Icons.sync),
                  label: const Text('Sync (Restore & Merge)'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(250, 50),
                    backgroundColor: Colors.teal.shade50,
                  ),
                ),
                const SizedBox(height: 15),
                ElevatedButton.icon(
                  onPressed: _handleUpload,
                  icon: const Icon(Icons.cloud_upload),
                  label: const Text('Backup to Cloud'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(250, 50),
                  ),
                ),
                const SizedBox(height: 15),
                ElevatedButton.icon(
                  onPressed: _handleCheckpoint,
                  icon: const Icon(Icons.bookmark_border),
                  label: const Text('Create Cloud Checkpoint'),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(250, 50),
                    foregroundColor: Colors.teal,
                  ),
                ),
                const SizedBox(height: 30),
                TextButton.icon(
                  onPressed: () async {
                    await _dropboxService.logout();
                    if (mounted) {
                      setState(() {
                        _isAuthenticated = false;
                        _statusMessage = "Disconnected";
                      });
                    }
                  },
                  icon: const Icon(Icons.link_off),
                  label: const Text('Unlink Dropbox'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
