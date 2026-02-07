import 'package:google_generative_ai/google_generative_ai.dart';
import 'base_provider.dart';

class GeminiProvider implements LLMProvider {
  final String apiKey;
  String? modelName;
  GenerativeModel? _model;

  GeminiProvider({required this.apiKey, this.modelName = 'gemini-1.5-flash'});

  @override
  String get providerName => "Google Gemini";

  GenerativeModel _getModel() {
    _model ??= GenerativeModel(
      model: modelName ?? 'gemini-1.5-flash',
      apiKey: apiKey,
    );
    return _model!;
  }

  @override
  Future<String?> generateResponse(
    String prompt, {
    int timeoutSeconds = 60,
  }) async {
    try {
      final model = _getModel();
      final content = [Content.text(prompt)];
      final response = await model.generateContent(content);
      return response.text;
    } catch (e) {
      print("Gemini Error: $e");
      return null;
    }
  }

  @override
  Future<bool> isAvailable() async {
    // Basic connectivity/auth check
    try {
      await generateResponse("Ping");
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<String>> getAvailableModels() async {
    return ['gemini-1.5-flash', 'gemini-1.5-pro'];
  }
}
