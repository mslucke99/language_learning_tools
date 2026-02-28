import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'llm_providers/base_provider.dart';
import 'llm_providers/gemini_provider.dart';
import 'llm_providers/openai_provider.dart';

class LLMService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  LLMProvider? _currentProvider;
  String _selectedProviderType = 'gemini'; // Default

  LLMProvider? get currentProvider => _currentProvider;
  String get selectedProviderType => _selectedProviderType;

  Future<void> initialize() async {
    _selectedProviderType =
        await _storage.read(key: 'llm_provider_type') ?? 'gemini';
    await _loadProvider();
  }

  Future<void> _loadProvider() async {
    final providerType = _selectedProviderType;
    final apiKey = await _storage.read(key: '${providerType}_api_key');
    final baseUrl = await _storage.read(key: '${providerType}_base_url');
    final modelName = await _storage.read(key: '${providerType}_model_name');

    if (providerType == 'gemini' && apiKey != null) {
      _currentProvider = GeminiProvider(
        apiKey: apiKey,
        modelName: modelName ?? 'gemini-1.5-flash',
      );
    } else if (providerType == 'openai' && apiKey != null) {
      _currentProvider = OpenAIProvider(
        apiKey: apiKey,
        baseUrl: baseUrl ?? 'https://api.openai.com/v1',
        modelName: modelName ?? 'gpt-3.5-turbo',
      );
    } else if (providerType == 'ollama') {
      // Ollama will be implemented next
      _currentProvider = OpenAIProvider(
        apiKey: 'ollama', // No key needed usually
        baseUrl: baseUrl ?? 'http://localhost:11434/v1',
        modelName: modelName ?? 'llama3',
      );
    } else {
      _currentProvider = null;
    }
    notifyListeners();
  }

  Future<void> setProvider(String type) async {
    _selectedProviderType = type;
    await _storage.write(key: 'llm_provider_type', value: type);
    await _loadProvider();
  }

  Future<void> updateProviderConfig(
    String type, {
    String? key,
    String? url,
    String? model,
  }) async {
    if (key != null) await _storage.write(key: '${type}_api_key', value: key);
    if (url != null) await _storage.write(key: '${type}_base_url', value: url);
    if (model != null)
      await _storage.write(key: '${type}_model_name', value: model);

    if (_selectedProviderType == type) await _loadProvider();
  }

  Future<void> updateGeminiKey(String key) async =>
      updateProviderConfig('gemini', key: key);

  Future<void> updateOpenAIConfig(String key, String url) async =>
      updateProviderConfig('openai', key: key, url: url);

  Future<String?> generate(String prompt) async {
    if (_currentProvider == null) return "No LLM Provider configured.";
    return await _currentProvider!.generateResponse(prompt);
  }

  /// Parse AI response to extract structured suggestions (flashcards, grammar patterns)
  static Map<String, dynamic> parseAISuggestions(String text) {
    final suggestions = {
      'flashcards': <Map<String, String>>[],
      'grammar': <Map<String, String>>[],
    };

    // Extract Flashcards: <flashcard word="TERM" context="CTX">DEF</flashcard>
    final flashcardRegex = RegExp(
      r'<flashcard\s+word\s*=\s*["'
      "'](.*?)["
      "'](?:\s+context\s*=\s*["
      "'](.*?)["
      "'])?>(.*?)</flashcard>",
      dotAll: true,
      caseSensitive: false,
    );

    for (final match in flashcardRegex.allMatches(text)) {
      suggestions['flashcards']?.add({
        'word': match.group(1) ?? '',
        'context': match.group(2) ?? '',
        'definition': (match.group(3) ?? '').trim(),
      });
    }

    // Extract Grammar: <grammar_pattern title="TITLE">EXP</grammar_pattern>
    final grammarRegex = RegExp(
      r'<grammar_pattern\s+title\s*=\s*["'
      "'](.*?)["
      "']>(.*?)</grammar_pattern>",
      dotAll: true,
      caseSensitive: false,
    );

    for (final match in grammarRegex.allMatches(text)) {
      suggestions['grammar']?.add({
        'title': match.group(1) ?? '',
        'explanation': (match.group(2) ?? '').trim(),
      });
    }

    // Clean text by removing tags
    String cleanText = text
        .replaceAll(flashcardRegex, '')
        .replaceAll(grammarRegex, '')
        .trim();

    return {'cleanText': cleanText, 'suggestions': suggestions};
  }
}
