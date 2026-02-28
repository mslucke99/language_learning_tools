import 'package:flutter/material.dart';
import '../services/statistics_service.dart';

class StatisticsDashboardScreen extends StatefulWidget {
  final String? language;

  const StatisticsDashboardScreen({
    super.key,
    this.language,
  });

  @override
  State<StatisticsDashboardScreen> createState() => _StatisticsDashboardScreenState();
}

class _StatisticsDashboardScreenState extends State<StatisticsDashboardScreen> {
  final StatisticsService _statsService = StatisticsService();
  
  Map<String, dynamic>? _overallStats;
  List<Map<String, dynamic>> _reviewHistory = [];
  bool _isLoading = true;
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _loadStatistics();
  }

  Future<void> _loadStatistics() async {
    setState(() => _isLoading = true);
    
    try {
      final stats = await _statsService.getOverallStats(
        language: widget.language,
        startDate: _startDate,
        endDate: _endDate,
      );
      
      final history = await _statsService.getReviewHistory(
        language: widget.language,
        startDate: _startDate,
        endDate: _endDate,
      );

      setState(() {
        _overallStats = stats;
        _reviewHistory = history;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading statistics: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistics'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadStatistics,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _overallStats == null
              ? const Center(child: Text('No statistics available'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _buildSummaryCards(),
                      const SizedBox(height: 24),
                      _buildReviewHistorySection(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildSummaryCards() {
    final totalReviews = _overallStats!['total_reviews'] as int;
    final correctReviews = _overallStats!['correct_reviews'] as int;
    final accuracy = _overallStats!['accuracy'] as double;
    final streak = _overallStats!['streak'] as int;
    final dueCards = _overallStats!['due_cards'] as int;

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildStatCard(
                'Total Reviews',
                totalReviews.toString(),
                Icons.school,
                Colors.blue,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                'Accuracy',
                '${accuracy.toStringAsFixed(1)}%',
                Icons.check_circle,
                Colors.green,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildStatCard(
                'Streak',
                '$streak days',
                Icons.local_fire_department,
                Colors.orange,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                'Due Today',
                dueCards.toString(),
                Icons.today,
                Colors.purple,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewHistorySection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Review History',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            if (_reviewHistory.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No review history available'),
                ),
              )
            else
              ..._reviewHistory.take(10).map((record) {
                final date = record['date'] as String;
                final count = record['count'] as int;
                final correct = record['correct'] as int;
                final accuracy = count > 0 ? (correct / count * 100) : 0.0;

                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Colors.teal,
                    child: Text(
                      count.toString(),
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                  title: Text(date),
                  subtitle: Text('$correct correct'),
                  trailing: Text(
                    '${accuracy.toStringAsFixed(0)}%',
                    style: TextStyle(
                      color: accuracy >= 80 ? Colors.green : Colors.orange,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                );
              }),
            if (_reviewHistory.length > 10)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Center(
                  child: Text(
                    'Showing 10 of ${_reviewHistory.length} days',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Statistics'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Last 7 days'),
              onTap: () {
                setState(() {
                  _startDate = DateTime.now().subtract(const Duration(days: 7));
                  _endDate = null;
                });
                Navigator.pop(context);
                _loadStatistics();
              },
            ),
            ListTile(
              title: const Text('Last 30 days'),
              onTap: () {
                setState(() {
                  _startDate = DateTime.now().subtract(const Duration(days: 30));
                  _endDate = null;
                });
                Navigator.pop(context);
                _loadStatistics();
              },
            ),
            ListTile(
              title: const Text('All time'),
              onTap: () {
                setState(() {
                  _startDate = null;
                  _endDate = null;
                });
                Navigator.pop(context);
                _loadStatistics();
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }
}
