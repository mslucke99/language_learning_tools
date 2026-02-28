import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/database_helper.dart';
import '../services/llm_service.dart';
import '../services/prompts.dart';
import 'package:uuid/uuid.dart';

class ChatSessionDetailScreen extends StatefulWidget {
  final Map<String, dynamic> session;

  const ChatSessionDetailScreen({super.key, required this.session});

  @override
  State<ChatSessionDetailScreen> createState() =>
      _ChatSessionDetailScreenState();
}

class _ChatSessionDetailScreenState extends State<ChatSessionDetailScreen> {
  final DatabaseHelper _dbHelper = DatabaseHelper();
  final TextEditingController _textController = TextEditingController();
  List<Map<String, dynamic>> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    final db = await _dbHelper.database;
    final messages = await db.query(
      'chat_messages',
      where: 'session_id = ? AND deleted_at IS NULL',
      whereArgs: [widget.session['id']],
      orderBy: 'created_at ASC',
    );

    if (mounted) {
      setState(() {
        _messages = messages;
        _isLoading = false;
      });
    }
  }

  Future<void> _handleSendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _isSending = true;
    });

    try {
      // 1. Save User Message
      final userMsg = {
        'session_id': widget.session['id'],
        'role': 'user',
        'content': text,
        'created_at': DateTime.now().toIso8601String(),
        'uuid': const Uuid().v4(),
      };
      await _dbHelper.insertItem('chat_messages', userMsg);
      _textController.clear();
      await _loadMessages();

      // 2. Trigger AI Response
      final llmService = Provider.of<LLMService>(context, listen: false);

      // Construct prompt with history (last few messages)
      String history = _messages
          .map((m) => "${m['role']}: ${m['content']}")
          .join("\n");

      final prompt =
          Prompts.format(Prompts.chatPrompts['system_roleplay']!['template']!, {
            'persona':
                widget.session['persona'] ??
                'Tutor', // persona should be in session data or default
            'study_language': widget.session['study_language'] ?? 'English',
            'native_language': 'English', // TODO: Get from settings
            'topic': widget.session['cur_topic'] ?? 'General Conversation',
          }) +
          "\n\nChat History:\n$history\n\nuser: $text";

      final response = await llmService.generate(prompt);

      if (response != null) {
        // Parse the XML-like response
        final reply = _extractTag(response, 'reply') ?? response;
        final feedback = _extractTag(response, 'feedback');
        final vocab = _extractTag(response, 'vocab');
        final grammar = _extractTag(response, 'grammar');

        final aiMsg = {
          'session_id': widget.session['id'],
          'role': 'assistant',
          'content': reply,
          'analysis': [
            feedback,
            vocab,
            grammar,
          ].where((s) => s != null).join("\n\n"),
          'created_at': DateTime.now().toIso8601String(),
          'uuid': const Uuid().v4(),
        };
        await _dbHelper.insertItem('chat_messages', aiMsg);
        await _loadMessages();
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error sending message: $e')));
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  String? _extractTag(String text, String tag) {
    final start = text.indexOf('<$tag>');
    final end = text.indexOf('</$tag>');
    if (start != -1 && end != -1) {
      return text.substring(start + tag.length + 2, end).trim();
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.session['cur_topic'] ?? 'Chat History'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                if (widget.session['study_language'] != null)
                  Container(
                    width: double.infinity,
                    color: Colors.teal.shade50,
                    padding: const EdgeInsets.symmetric(
                      vertical: 8,
                      horizontal: 16,
                    ),
                    child: Text(
                      'Target Language: ${widget.session['study_language']}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.teal,
                      ),
                    ),
                  ),
                Expanded(
                  child: _messages.isEmpty
                      ? const Center(
                          child: Text('No messages found in this session.'),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _messages.length,
                          itemBuilder: (context, index) {
                            final msg = _messages[index];
                            final bool isUser = msg['role'] == 'user';
                            return _buildMessageBubble(msg, isUser);
                          },
                        ),
                ),
                _buildInputArea(),
              ],
            ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(8.0),
      color: Colors.white,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              decoration: const InputDecoration(
                hintText: 'Type your message...',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _handleSendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _isSending ? null : _handleSendMessage,
            icon: _isSending
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send, color: Colors.teal),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(Map<String, dynamic> msg, bool isUser) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        decoration: BoxDecoration(
          color: isUser ? Colors.teal.shade100 : Colors.grey.shade200,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 0),
            bottomRight: Radius.circular(isUser ? 0 : 16),
          ),
          border: Border.all(
            color: isUser ? Colors.teal.shade200 : Colors.grey.shade300,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              msg['content'] ?? '',
              style: const TextStyle(fontSize: 16, height: 1.4),
            ),
            if (msg['analysis'] != null &&
                msg['analysis'].toString().isNotEmpty) ...[
              const Divider(),
              const Text(
                'AI Analysis:',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.indigo,
                ),
              ),
              Text(
                msg['analysis'].toString(),
                style: const TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
