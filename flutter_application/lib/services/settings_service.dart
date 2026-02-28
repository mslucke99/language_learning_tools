import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SettingsService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  String _studyLanguage = 'Spanish';
  String _nativeLanguage = 'English';
  int _requestTimeout = 120;
  String _uiLocale = 'en';

  String get studyLanguage => _studyLanguage;
  String get nativeLanguage => _nativeLanguage;
  int get requestTimeout => _requestTimeout;
  String get uiLocale => _uiLocale;

  Future<void> initialize() async {
    _studyLanguage = await _storage.read(key: 'study_language') ?? 'Spanish';
    _nativeLanguage = await _storage.read(key: 'native_language') ?? 'English';
    _requestTimeout = int.parse(
      await _storage.read(key: 'request_timeout') ?? '120',
    );
    _uiLocale = await _storage.read(key: 'ui_locale') ?? 'en';
    notifyListeners();
  }

  Future<void> setStudyLanguage(String language) async {
    _studyLanguage = language;
    await _storage.write(key: 'study_language', value: language);
    notifyListeners();
  }

  Future<void> setNativeLanguage(String language) async {
    _nativeLanguage = language;
    await _storage.write(key: 'native_language', value: language);
    notifyListeners();
  }

  Future<void> setRequestTimeout(int timeout) async {
    _requestTimeout = timeout;
    await _storage.write(key: 'request_timeout', value: timeout.toString());
    notifyListeners();
  }

  Future<void> setUiLocale(String locale) async {
    _uiLocale = locale;
    await _storage.write(key: 'ui_locale', value: locale);
    notifyListeners();
  }

  // Prompt Management
  Future<String?> getCustomPrompt(
    String category,
    String promptId,
    String templateType,
  ) async {
    return await _storage.read(key: 'prompt:$category:$promptId:$templateType');
  }

  Future<void> setCustomPrompt(
    String category,
    String promptId,
    String templateType,
    String value,
  ) async {
    await _storage.write(
      key: 'prompt:$category:$promptId:$templateType',
      value: value,
    );
    notifyListeners();
  }

  Future<void> resetPrompt(
    String category,
    String promptId,
    String templateType,
  ) async {
    await _storage.delete(key: 'prompt:$category:$promptId:$templateType');
    notifyListeners();
  }

  Future<void> resetAllPrompts() async {
    // Note: FlutterSecureStorage doesn't support deleting by prefix easily.
    // In a real database we'd use LIKE, but here we might need to track keys.
    // For now, we'll just delete the known ones or leave as is if complex.
    // A better way would be using a dedicated setting for "has_custom_prompts"
    // or switching prompt storage to SQLite if it grows.
  }
}
