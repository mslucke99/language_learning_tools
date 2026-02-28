import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/chat_service.dart';
import 'package:proficiency_suites/services/roleplay_service.dart';
import 'package:proficiency_suites/services/settings_service.dart';

class ActiveChatScreen extends StatefulWidget {
  final int? sessionId;
  final String? topic;
  final bool isRoleplay;

  const ActiveChatScreen({
    super.key,
    this.sessionId,
    this.topic,
    this.isRoleplay = false,
  });

  @override
  State<ActiveChatScreen> createState() => _ActiveChatScreenState();
}

class _ActiveChatScreenState extends State<ActiveChatScreen>
    with SingleTickerProviderStateMixin {
  late ChatService _chatService;
  final RoleplayService _roleplayService = RoleplayService();
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  List<ChatMessage> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;

  late TabController _tabController;
  String _currentFeedback = '';
  String _currentVocab = '';
  String _currentGrammar = '';

  ChatSession? _session;
  RoleplayScenario? _scenario;

  @override
  void initState() {
    super.initState();
    // ChatService will be initialized in didChangeDependencies or build if needed,
    // but here we can just wait for context to be available in build or didChangeDependencies.
  }

  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      final settings = Provider.of<SettingsService>(context);
      _chatService = ChatService(settings);
      _tabController = TabController(
        length: widget.isRoleplay ? 4 : 3,
        vsync: this,
      );
      _loadSession();
      _loadMessages();
      _initialized = true;
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadSession() async {
    if (widget.sessionId == null) return;

    try {
      final session = await _chatService.getSession(widget.sessionId!);
      setState(() => _session = session);

      // Load scenario if roleplay mode
      if (widget.isRoleplay && session?.scenarioId != null) {
        final scenario = await _roleplayService.getScenario(
          session!.scenarioId!,
        );
        setState(() => _scenario = scenario);
      }
    } catch (e) {
      // Ignore errors
    }
  }

  Future<void> _loadMessages() async {
    if (widget.sessionId == null) return;

    setState(() => _isLoading = true);

    try {
      final messages = await _chatService.getMessages(widget.sessionId!);

      setState(() {
        _messages = messages;
        _isLoading = false;
      });

      _scrollToBottom();

      // Load analysis from last message
      if (messages.isNotEmpty) {
        final lastMessage = messages.last;
        if (lastMessage.analysis != null) {
          _parseAnalysis(lastMessage.analysis!);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error loading messages: $e')));
      }
      setState(() => _isLoading = false);
    }
  }

  void _parseAnalysis(String analysisJson) {
    try {
      final analysis = jsonDecode(analysisJson);

      setState(() {
        _currentFeedback = analysis['feedback'] ?? '';
        _currentVocab = analysis['vocab_section'] ?? '';
        _currentGrammar = analysis['grammar_section'] ?? '';
      });
    } catch (e) {
      // Ignore parsing errors
    }
  }

  Future<void> _sendMessage() async {
    if (widget.sessionId == null) return;

    final message = _messageController.text.trim();
    if (message.isEmpty || _isSending) return;

    _messageController.clear();
    setState(() => _isSending = true);

    // Add user message to UI immediately
    final userMessage = ChatMessage(
      sessionId: widget.sessionId!,
      role: 'user',
      content: message,
      createdAt: DateTime.now().toIso8601String(),
    );

    setState(() {
      _messages.add(userMessage);
    });

    _scrollToBottom();

    try {
      final response = await _chatService.sendMessage(
        widget.sessionId!,
        message,
      );

      setState(() {
        _messages.add(response);
        _isSending = false;
      });

      // Parse analysis
      if (response.analysis != null) {
        _parseAnalysis(response.analysis!);
      }

      _scrollToBottom();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error sending message: $e')));
      }
      setState(() => _isSending = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.isRoleplay
        ? '🎭 ${_scenario?.name ?? widget.topic ?? "Roleplay"}'
        : '💬 ${widget.topic ?? "Chat"}';

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: widget.isRoleplay && _scenario != null
            ? [
                IconButton(
                  icon: const Icon(Icons.info_outline),
                  onPressed: _showScenarioInfo,
                ),
              ]
            : null,
      ),
      body: Row(
        children: [
          // Chat area (left side)
          Expanded(
            flex: 3,
            child: Column(
              children: [
                // Messages
                Expanded(
                  child: _isLoading
                      ? const Center(child: CircularProgressIndicator())
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          itemCount: _messages.length + (_isSending ? 1 : 0),
                          itemBuilder: (context, index) {
                            if (index == _messages.length && _isSending) {
                              return const Padding(
                                padding: EdgeInsets.symmetric(vertical: 8.0),
                                child: Row(
                                  children: [
                                    CircularProgressIndicator(),
                                    SizedBox(width: 16),
                                    Text('Tutor is typing...'),
                                  ],
                                ),
                              );
                            }

                            final message = _messages[index];
                            final isUser = message.role == 'user';

                            return Align(
                              alignment: isUser
                                  ? Alignment.centerRight
                                  : Alignment.centerLeft,
                              child: Container(
                                margin: const EdgeInsets.symmetric(vertical: 4),
                                padding: const EdgeInsets.all(12),
                                constraints: BoxConstraints(
                                  maxWidth:
                                      MediaQuery.of(context).size.width * 0.7,
                                ),
                                decoration: BoxDecoration(
                                  color: isUser
                                      ? Colors.blue[100]
                                      : Colors.grey[200],
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      isUser ? 'You' : 'Tutor',
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: isUser
                                            ? Colors.blue[900]
                                            : Colors.green[900],
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      message.content,
                                      style: const TextStyle(fontSize: 16),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),

                // Input area
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.grey.withOpacity(0.2),
                        spreadRadius: 1,
                        blurRadius: 3,
                        offset: const Offset(0, -1),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _messageController,
                          decoration: const InputDecoration(
                            hintText: 'Type your message...',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: null,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _sendMessage(),
                          enabled: !_isSending,
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        onPressed: _isSending ? null : _sendMessage,
                        icon: const Icon(Icons.send),
                        color: Theme.of(context).primaryColor,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Analysis panel (right side)
          Container(
            width: 300,
            decoration: BoxDecoration(
              border: Border(left: BorderSide(color: Colors.grey[300]!)),
            ),
            child: Column(
              children: [
                TabBar(
                  controller: _tabController,
                  labelColor: Colors.teal,
                  tabs: widget.isRoleplay
                      ? const [
                          Tab(text: 'Scenario'),
                          Tab(text: 'Feedback'),
                          Tab(text: 'Vocabulary'),
                          Tab(text: 'Grammar'),
                        ]
                      : const [
                          Tab(text: 'Feedback'),
                          Tab(text: 'Vocabulary'),
                          Tab(text: 'Grammar'),
                        ],
                ),
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: widget.isRoleplay
                        ? [
                            // Scenario tab (roleplay only)
                            _buildScenarioTab(),

                            // Feedback tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentFeedback.isEmpty
                                    ? 'Feedback will appear here after you send a message.'
                                    : _currentFeedback,
                              ),
                            ),

                            // Vocabulary tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentVocab.isEmpty
                                    ? 'Vocabulary suggestions will appear here.'
                                    : _currentVocab,
                              ),
                            ),

                            // Grammar tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentGrammar.isEmpty
                                    ? 'Grammar explanations will appear here.'
                                    : _currentGrammar,
                              ),
                            ),
                          ]
                        : [
                            // Feedback tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentFeedback.isEmpty
                                    ? 'Feedback will appear here after you send a message.'
                                    : _currentFeedback,
                              ),
                            ),

                            // Vocabulary tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentVocab.isEmpty
                                    ? 'Vocabulary suggestions will appear here.'
                                    : _currentVocab,
                              ),
                            ),

                            // Grammar tab
                            SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Text(
                                _currentGrammar.isEmpty
                                    ? 'Grammar explanations will appear here.'
                                    : _currentGrammar,
                              ),
                            ),
                          ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScenarioTab() {
    if (_scenario == null) {
      return const Center(child: Text('Loading scenario...'));
    }

    final characters = _roleplayService.parseCharacters(_scenario!.characters);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Your Role',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Colors.deepPurple,
            ),
          ),
          const SizedBox(height: 8),
          Text(_scenario!.userRole),
          const SizedBox(height: 16),
          Text(
            'Situation',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Colors.deepPurple,
            ),
          ),
          const SizedBox(height: 8),
          Text(_scenario!.situation),
          const SizedBox(height: 16),
          Text(
            'Characters',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Colors.deepPurple,
            ),
          ),
          const SizedBox(height: 8),
          ...characters.map(
            (char) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              color: Colors.deepPurple.shade50,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      char['name'] ?? 'Unknown',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    if (char['role'] != null) Text('Role: ${char['role']}'),
                    if (char['personality'] != null)
                      Text('Personality: ${char['personality']}'),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showScenarioInfo() {
    if (_scenario == null) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_scenario!.name),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (_scenario!.description != null) ...[
                Text(_scenario!.description!),
                const SizedBox(height: 16),
              ],
              Text(
                'Your Role: ${_scenario!.userRole}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
