abstract class LLMProvider {
  String get providerName;
  Future<String?> generateResponse(String prompt, {int timeoutSeconds = 60});
  Future<bool> isAvailable();
  Future<List<String>> getAvailableModels();
}
