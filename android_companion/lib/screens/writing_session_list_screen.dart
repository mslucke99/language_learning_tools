import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import 'writing_session_detail_screen.dart';

class WritingSessionListScreen extends StatefulWidget {
  const WritingSessionListScreen({super.key});

  @override
  State<WritingSessionListScreen> createState() =>
      _WritingSessionListScreenState();
}

class _WritingSessionListScreenState extends State<WritingSessionListScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  List<Map<String, dynamic>> _sessions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    final db = await _dbHelper.database;
    final tableExists = (await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='writing_sessions'",
    )).isNotEmpty;

    if (!tableExists) {
      if (mounted) {
        setState(() {
          _sessions = [];
          _isLoading = false;
        });
      }
      return;
    }

    final List<Map<String, dynamic>> sessions = await db.query(
      'writing_sessions',
      where: 'deleted_at IS NULL',
      orderBy: 'created_at DESC',
    );

    if (mounted) {
      setState(() {
        _sessions = List.from(sessions);
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteSession(Map<String, dynamic> session) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete ${session['topic']}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _dbHelper.softDelete('writing_sessions', session['id']);
      _loadSessions();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Writing History'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _sessions.isEmpty
          ? const Center(child: Text('No writing sessions found.'))
          : ListView.builder(
              itemCount: _sessions.length,
              itemBuilder: (context, index) {
                final session = _sessions[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.edit_note, color: Colors.indigo),
                    title: Text(
                      session['topic'] ?? 'Untitled Session',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Grade: ${session['grade'] ?? 'N/A'} • ${session['created_at'] != null ? session['created_at'].toString().split('T')[0] : ''}',
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      onPressed: () => _deleteSession(session),
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) =>
                              WritingSessionDetailScreen(session: session),
                        ),
                      ).then((_) => _loadSessions());
                    },
                  ),
                );
              },
            ),
    );
  }
}
