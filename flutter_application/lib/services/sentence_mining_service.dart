import 'package:proficiency_suites/services/database_helper.dart';
import 'package:proficiency_suites/services/known_words_service.dart';

class SentenceMiningService {
  final DatabaseHelper _db = DatabaseHelper();
  final KnownWordsService _knownWordsService;

  SentenceMiningService(this._knownWordsService);

  /// Analyze text and return sentences with difficulty scores
  Future<List<Map<String, dynamic>>> analyzeText(
    String text,
    String language,
  ) async {
    // Split text into sentences
    final sentences = _splitIntoSentences(text);
    
    // Get known words for the language
    final knownWords = await _knownWordsService.getKnownWords(language);
    final knownLemmas = knownWords.map((w) => w.lemma).toSet();

    // Score each sentence
    List<Map<String, dynamic>> results = [];
    for (var sentence in sentences) {
      if (sentence.trim().isEmpty) continue;
      
      final score = await scoreSentence(sentence, knownLemmas);
      final unknownWords = extractUnknownWords(sentence, knownLemmas);
      
      results.add({
        'sentence': sentence,
        'difficulty_score': score,
        'unknown_words': unknownWords,
        'total_words': _extractWords(sentence).length,
        'known_words': _extractWords(sentence).length - unknownWords.length,
      });
    }

    return results;
  }

  /// Calculate difficulty score for a sentence
  Future<double> scoreSentence(String sentence, Set<String> knownWords) async {
    final words = _extractWords(sentence);
    if (words.isEmpty) return 0.0;

    int knownCount = 0;
    for (var word in words) {
      if (knownWords.contains(word.toLowerCase())) {
        knownCount++;
      }
    }

    // Base difficulty: 1.0 - (known_words / total_words)
    double baseDifficulty = 1.0 - (knownCount / words.length);

    // Adjust for sentence length (longer = slightly harder)
    double lengthFactor = 1.0;
    if (words.length > 20) {
      lengthFactor = 1.1;
    } else if (words.length > 30) {
      lengthFactor = 1.2;
    }

    return (baseDifficulty * lengthFactor).clamp(0.0, 1.0);
  }

  /// Extract unknown words from a sentence
  List<String> extractUnknownWords(String sentence, Set<String> knownWords) {
    final words = _extractWords(sentence);
    return words
        .where((word) => !knownWords.contains(word.toLowerCase()))
        .toList();
  }

  /// Filter sentences by difficulty range
  List<Map<String, dynamic>> filterByDifficulty(
    List<Map<String, dynamic>> sentences,
    double minScore,
    double maxScore,
  ) {
    return sentences
        .where((s) =>
            s['difficulty_score'] >= minScore &&
            s['difficulty_score'] <= maxScore)
        .toList();
  }

  /// Save sentences to imported content
  Future<List<int>> saveSentences(
    List<String> sentences,
    String language,
    String sourceUrl,
  ) async {
    List<int> ids = [];
    
    for (var sentence in sentences) {
      final id = await _db.insertItem('imported_content', {
        'content_type': 'sentence',
        'content': sentence,
        'url': sourceUrl,
        'language': language,
        'created_at': DateTime.now().toIso8601String(),
        'processed': 0,
      });
      ids.add(id);
    }

    return ids;
  }

  /// Split text into sentences
  List<String> _splitIntoSentences(String text) {
    // Simple sentence splitting (can be improved with language-specific rules)
    return text
        .split(RegExp(r'[.!?]+'))
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  /// Extract words from text
  List<String> _extractWords(String text) {
    return text
        .replaceAll(RegExp(r'[^\w\s]'), ' ')
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty && w.length > 1)
        .toList();
  }

  /// Get difficulty level label
  String getDifficultyLabel(double score) {
    if (score < 0.2) return 'Very Easy';
    if (score < 0.4) return 'Easy';
    if (score < 0.6) return 'Medium';
    if (score < 0.8) return 'Hard';
    return 'Very Hard';
  }

  /// Get difficulty color
  int getDifficultyColor(double score) {
    if (score < 0.2) return 0xFF4CAF50; // Green
    if (score < 0.4) return 0xFF8BC34A; // Light Green
    if (score < 0.6) return 0xFFFFC107; // Amber
    if (score < 0.8) return 0xFFFF9800; // Orange
    return 0xFFF44336; // Red
  }
}
