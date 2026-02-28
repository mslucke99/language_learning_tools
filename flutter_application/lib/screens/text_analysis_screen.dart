import 'package:flutter/material.dart';
import '../services/sentence_mining_service.dart';
import '../services/known_words_service.dart';

class TextAnalysisScreen extends StatefulWidget {
  final String language;

  const TextAnalysisScreen({
    super.key,
    required this.language,
  });

  @override
  State<TextAnalysisScreen> createState() => _TextAnalysisScreenState();
}

class _TextAnalysisScreenState extends State<TextAnalysisScreen> with SingleTickerProviderStateMixin {
  late SentenceMiningService _miningService;
  final KnownWordsService _knownWordsService = KnownWordsService();
  final TextEditingController _textController = TextEditingController();
  
  late TabController _tabController;
  bool _isAnalyzing = false;
  
  List<String> _vocabulary = [];
  Map<String, int> _wordFrequency = {};
  List<Map<String, dynamic>> _sentences = [];
  String _cefrLevel = '';

  @override
  void initState() {
    super.initState();
    _miningService = SentenceMiningService(_knownWordsService);
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _textController.dispose();
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _analyzeText() async {
    if (_textController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter some text')),
      );
      return;
    }

    setState(() => _isAnalyzing = true);

    try {
      // Extract vocabulary
      final words = _extractWords(_textController.text);
      final uniqueWords = words.toSet().toList()..sort();
      
      // Calculate word frequency
      final frequency = <String, int>{};
      for (var word in words) {
        frequency[word] = (frequency[word] ?? 0) + 1;
      }
      
      // Analyze sentences
      final sentences = await _miningService.analyzeText(
        _textController.text,
        widget.language,
      );
      
      // Estimate CEFR level
      final level = _estimateCEFRLevel(uniqueWords.length);

      setState(() {
        _vocabulary = uniqueWords;
        _wordFrequency = frequency;
        _sentences = sentences;
        _cefrLevel = level;
        _isAnalyzing = false;
      });
    } catch (e) {
      setState(() => _isAnalyzing = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  List<String> _extractWords(String text) {
    return text
        .toLowerCase()
        .replaceAll(RegExp(r'[^\w\s]'), ' ')
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty && w.length > 1)
        .toList();
  }

  String _estimateCEFRLevel(int uniqueWordCount) {
    if (uniqueWordCount < 500) return 'A1 (Beginner)';
    if (uniqueWordCount < 1000) return 'A2 (Elementary)';
    if (uniqueWordCount < 2000) return 'B1 (Intermediate)';
    if (uniqueWordCount < 3500) return 'B2 (Upper Intermediate)';
    if (uniqueWordCount < 5000) return 'C1 (Advanced)';
    return 'C2 (Proficient)';
  }

  Future<void> _addWordsToKnown(List<String> words) async {
    final count = await _knownWordsService.addWordsBulk(
      words,
      widget.language,
      source: 'import',
    );
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Added $count words to known words')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Text Analysis'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(
                  controller: _textController,
                  decoration: const InputDecoration(
                    labelText: 'Paste text to analyze',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 6,
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isAnalyzing ? null : _analyzeText,
                    icon: const Icon(Icons.analytics),
                    label: const Text('Analyze Text'),
                  ),
                ),
              ],
            ),
          ),
          if (_vocabulary.isNotEmpty) ...[
            TabBar(
              controller: _tabController,
              labelColor: Colors.teal,
              tabs: const [
                Tab(text: 'Vocabulary'),
                Tab(text: 'Frequency'),
                Tab(text: 'Sentences'),
              ],
            ),
            Expanded(
              child: _isAnalyzing
                  ? const Center(child: CircularProgressIndicator())
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildVocabularyTab(),
                        _buildFrequencyTab(),
                        _buildSentencesTab(),
                      ],
                    ),
            ),
          ] else if (_isAnalyzing)
            const Expanded(
              child: Center(child: CircularProgressIndicator()),
            )
          else
            const Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.text_snippet, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text('Paste text above and analyze'),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildVocabularyTab() {
    return Column(
      children: [
        Card(
          margin: const EdgeInsets.all(16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Unique Words',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          _vocabulary.length.toString(),
                          style: const TextStyle(
                            fontSize: 24,
                            color: Colors.teal,
                          ),
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text(
                          'CEFR Level',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          _cefrLevel,
                          style: const TextStyle(
                            fontSize: 16,
                            color: Colors.deepPurple,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () => _addWordsToKnown(_vocabulary),
                    icon: const Icon(Icons.add),
                    label: const Text('Add All to Known Words'),
                  ),
                ),
              ],
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: _vocabulary.length,
            itemBuilder: (context, index) {
              final word = _vocabulary[index];
              final frequency = _wordFrequency[word] ?? 0;
              
              return ListTile(
                title: Text(word),
                trailing: Chip(
                  label: Text('×$frequency'),
                  backgroundColor: Colors.teal.shade100,
                ),
                onTap: () async {
                  await _knownWordsService.addWord(word, widget.language);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Added "$word" to known words')),
                    );
                  }
                },
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildFrequencyTab() {
    final sortedWords = _wordFrequency.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sortedWords.length,
      itemBuilder: (context, index) {
        final entry = sortedWords[index];
        final maxFrequency = sortedWords.first.value;
        final percentage = (entry.value / maxFrequency * 100).round();

        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      entry.key,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      '${entry.value} times',
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: percentage / 100,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.teal),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSentencesTab() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _sentences.length,
      itemBuilder: (context, index) {
        final sentence = _sentences[index];
        final text = sentence['sentence'] as String;
        final score = sentence['difficulty_score'] as double;
        final unknownWords = sentence['unknown_words'] as List<String>;

        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Color(_miningService.getDifficultyColor(score)),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _miningService.getDifficultyLabel(score),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(text),
                if (unknownWords.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: unknownWords.map((word) => Chip(
                      label: Text(word),
                      backgroundColor: Colors.orange.shade100,
                      labelStyle: const TextStyle(fontSize: 12),
                    )).toList(),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
