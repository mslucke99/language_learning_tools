import 'dart:convert';
import 'package:http/http.dart' as http;
import 'base_provider.dart';

class OpenAIProvider implements LLMProvider {
  final String apiKey;
  final String? baseUrl;
  String modelName;

  OpenAIProvider({
    required this.apiKey,
    this.baseUrl = 'https://api.openai.com/v1',
    this.modelName = 'gpt-3.5-turbo',
  });

  @override
  String get providerName => "OpenAI";

  @override
  Future<String?> generateResponse(
    String prompt, {
    int timeoutSeconds = 60,
  }) async {
    final url = Uri.parse('$baseUrl/chat/completions');

    try {
      final response = await http
          .post(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $apiKey',
            },
            body: jsonEncode({
              'model': modelName,
              'messages': [
                {'role': 'user', 'content': prompt},
              ],
            }),
          )
          .timeout(Duration(seconds: timeoutSeconds));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['choices'][0]['message']['content'];
      } else {
        print("OpenAI Error: ${response.statusCode} ${response.body}");
        return null;
      }
    } catch (e) {
      print("OpenAI Error: $e");
      return null;
    }
  }

  @override
  Future<bool> isAvailable() async {
    try {
      final res = await generateResponse("Ping");
      return res != null;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<String>> getAvailableModels() async {
    return ['gpt-3.5-turbo', 'gpt-4', 'gpt-4o'];
  }
}
