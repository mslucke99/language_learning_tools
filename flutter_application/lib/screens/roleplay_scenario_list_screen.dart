import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/roleplay_service.dart';
import 'active_chat_screen.dart';

class RoleplayScenarioListScreen extends StatefulWidget {
  final String? language;

  const RoleplayScenarioListScreen({
    super.key,
    this.language,
  });

  @override
  State<RoleplayScenarioListScreen> createState() => _RoleplayScenarioListScreenState();
}

class _RoleplayScenarioListScreenState extends State<RoleplayScenarioListScreen> {
  final RoleplayService _roleplayService = RoleplayService();
  List<RoleplayScenario> _scenarios = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadScenarios();
  }

  Future<void> _loadScenarios() async {
    setState(() => _isLoading = true);
    
    try {
      final scenarios = await _roleplayService.getScenarios();
      setState(() {
        _scenarios = scenarios;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading scenarios: $e')),
        );
      }
    }
  }

  Future<void> _startRoleplay(RoleplayScenario scenario) async {
    try {
      final sessionId = await _roleplayService.startRoleplaySession(
        scenario.id!,
        widget.language ?? 'Unknown',
      );

      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ActiveChatScreen(
              sessionId: sessionId,
              isRoleplay: true,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error starting roleplay: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Roleplay Scenarios'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadScenarios,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _scenarios.isEmpty
              ? const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.theater_comedy, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text('No roleplay scenarios found'),
                      SizedBox(height: 8),
                      Text(
                        'Scenarios will sync from your desktop app',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _scenarios.length,
                  itemBuilder: (context, index) {
                    final scenario = _scenarios[index];
                    return _buildScenarioCard(scenario);
                  },
                ),
    );
  }

  Widget _buildScenarioCard(RoleplayScenario scenario) {
    final characters = _roleplayService.getCharacterNames(scenario);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      child: InkWell(
        onTap: () => _showScenarioDetails(scenario),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.theater_comedy, color: Colors.deepPurple),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      scenario.name,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ),
                ],
              ),
              if (scenario.description != null) ...[
                const SizedBox(height: 8),
                Text(
                  scenario.description!,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  const Icon(Icons.person, size: 16, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    'Your role: ${scenario.userRole}',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.people, size: 16, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    'Characters: ${characters.join(", ")}',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: () => _startRoleplay(scenario),
                icon: const Icon(Icons.play_arrow),
                label: const Text('Start Roleplay'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepPurple,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showScenarioDetails(RoleplayScenario scenario) {
    final characters = _roleplayService.parseCharacters(scenario.characters);
    
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                scenario.name,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 16),
              Text(
                'Situation',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Colors.teal,
                    ),
              ),
              const SizedBox(height: 8),
              Text(scenario.situation),
              const SizedBox(height: 16),
              Text(
                'Your Role',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Colors.teal,
                    ),
              ),
              const SizedBox(height: 8),
              Text(scenario.userRole),
              const SizedBox(height: 16),
              Text(
                'Characters',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Colors.teal,
                    ),
              ),
              const SizedBox(height: 8),
              ...characters.map((char) => Card(
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
                          if (char['role'] != null)
                            Text('Role: ${char['role']}'),
                          if (char['personality'] != null)
                            Text('Personality: ${char['personality']}'),
                        ],
                      ),
                    ),
                  )),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                    _startRoleplay(scenario);
                  },
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start Roleplay'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepPurple,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.all(16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
