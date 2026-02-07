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
    final geminiKey = await _storage.read(key: 'gemini_api_key');
    final openaiKey = await _storage.read(key: 'openai_api_key');
    final openaiUrl =
        await _storage.read(key: 'openai_base_url') ??
        'https://api.openai.com/v1';

    if (_selectedProviderType == 'gemini' && geminiKey != null) {
      _currentProvider = GeminiProvider(apiKey: geminiKey);
    } else if (_selectedProviderType == 'openai' && openaiKey != null) {
      _currentProvider = OpenAIProvider(apiKey: openaiKey, baseUrl: openaiUrl);
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

  Future<void> updateGeminiKey(String key) async {
    await _storage.write(key: 'gemini_api_key', value: key);
    if (_selectedProviderType == 'gemini') await _loadProvider();
  }

  Future<void> updateOpenAIConfig(String key, String url) async {
    await _storage.write(key: 'openai_api_key', value: key);
    await _storage.write(key: 'openai_base_url', value: url);
    if (_selectedProviderType == 'openai') await _loadProvider();
  }

  Future<String?> generate(String prompt) async {
    if (_currentProvider == null) return "No LLM Provider configured.";
    return await _currentProvider!.generateResponse(prompt);
  }
}
