import 'package:flutter/material.dart';
import '../services/sentence_mining_service.dart';
import '../services/known_words_service.dart';

class SentenceMiningScreen extends StatefulWidget {
  final String language;

  const SentenceMiningScreen({
    super.key,
    required this.language,
  });

  @override
  State<SentenceMiningScreen> createState() => _SentenceMiningScreenState();
}

class _SentenceMiningScreenState extends State<SentenceMiningScreen> {
  late SentenceMiningService _miningService;
  final KnownWordsService _knownWordsService = KnownWordsService();
  final TextEditingController _textController = TextEditingController();
  
  List<Map<String, dynamic>> _sentences = [];
  bool _isAnalyzing = false;
  double _minDifficulty = 0.0;
  double _maxDifficulty = 1.0;
  Set<String> _addedWords = {};

  @override
  void initState() {
    super.initState();
    _miningService = SentenceMiningService(_knownWordsService);
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
      final results = await _miningService.analyzeText(
        _textController.text,
        widget.language,
      );

      setState(() {
        _sentences = results;
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

  List<Map<String, dynamic>> get _filteredSentences {
    return _miningService.filterByDifficulty(
      _sentences,
      _minDifficulty,
      _maxDifficulty,
    );
  }

  Future<void> _saveSentences(List<String> sentences) async {
    try {
      await _miningService.saveSentences(
        sentences,
        widget.language,
        'sentence_mining',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Saved ${sentences.length} sentences')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving: $e')),
        );
      }
    }
  }

  Future<void> _addWordToKnown(String word) async {
    if (_addedWords.contains(word)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Word "$word" already added')),
      );
      return;
    }

    try {
      final result = await _knownWordsService.addWord(
        word,
        widget.language,
        source: 'sentence_mining',
      );

      if (mounted) {
        if (result > 0) {
          setState(() => _addedWords.add(word));
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Added "$word" to known words')),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Word "$word" is already known')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding word: $e')),
        );
      }
    }
  }

  Future<void> _addAllUnknownWords(List<String> words) async {
    // Filter out words already added in this session
    final wordsToAdd = words.where((w) => !_addedWords.contains(w)).toList();
    
    if (wordsToAdd.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All words already added')),
      );
      return;
    }

    try {
      final count = await _knownWordsService.addWordsBulk(
        wordsToAdd,
        widget.language,
        source: 'sentence_mining',
      );

      if (mounted) {
        setState(() => _addedWords.addAll(wordsToAdd));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Added $count words to known words')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error adding words: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sentence Mining'),
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
                  maxLines: 8,
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
          if (_sentences.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Difficulty Filter',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Text(_miningService.getDifficultyLabel(_minDifficulty)),
                          Expanded(
                            child: RangeSlider(
                              values: RangeValues(_minDifficulty, _maxDifficulty),
                              min: 0.0,
                              max: 1.0,
                              divisions: 10,
                              labels: RangeLabels(
                                _miningService.getDifficultyLabel(_minDifficulty),
                                _miningService.getDifficultyLabel(_maxDifficulty),
                              ),
                              onChanged: (values) {
                                setState(() {
                                  _minDifficulty = values.start;
                                  _maxDifficulty = values.end;
                                });
                              },
                            ),
                          ),
                          Text(_miningService.getDifficultyLabel(_maxDifficulty)),
                        ],
                      ),
                      Text(
                        'Showing ${_filteredSentences.length} of ${_sentences.length} sentences',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Expanded(
              child: _isAnalyzing
                  ? const Center(child: CircularProgressIndicator())
                  : _filteredSentences.isEmpty
                      ? const Center(
                          child: Text('No sentences match the difficulty filter'),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredSentences.length,
                          itemBuilder: (context, index) {
                            final sentence = _filteredSentences[index];
                            return _buildSentenceCard(sentence);
                          },
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
                    Icon(Icons.text_fields, size: 64, color: Colors.grey),
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

  Widget _buildSentenceCard(Map<String, dynamic> sentence) {
    final text = sentence['sentence'] as String;
    final score = sentence['difficulty_score'] as double;
    final unknownWords = sentence['unknown_words'] as List<String>;
    final totalWords = sentence['total_words'] as int;
    final knownWords = sentence['known_words'] as int;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
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
                const Spacer(),
                Text(
                  '$knownWords/$totalWords known',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              text,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (unknownWords.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Unknown words:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: unknownWords.map((word) => ActionChip(
                  label: Text(word),
                  backgroundColor: Colors.orange.shade100,
                  labelStyle: const TextStyle(fontSize: 12),
                  onPressed: () => _addWordToKnown(word),
                )).toList(),
              ),
            ],
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (unknownWords.isNotEmpty)
                  TextButton.icon(
                    onPressed: () => _addAllUnknownWords(unknownWords),
                    icon: const Icon(Icons.add_circle_outline, size: 16),
                    label: const Text('Add All Unknown'),
                  ),
                TextButton.icon(
                  onPressed: () => _saveSentences([text]),
                  icon: const Icon(Icons.save, size: 16),
                  label: const Text('Save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }
}
