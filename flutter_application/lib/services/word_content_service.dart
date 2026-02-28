/// Word Content Service
/// 
/// Manages AI-generated content for words: definitions and examples.

import 'dart:convert';
import '../models/word_definition.dart';
import 'database_helper.dart';
import 'llm_service.dart';

class WordContentService {
  final DatabaseHelper _db;
  final LLMService _llm;
  
  WordContentService(this._db, this._llm);
  
  /// Generate definition for a word
  Future<WordDefinition> generateDefinition({
    required int importedContentId,
    required String word,
    required String language,
    bool useNativeLanguage = true,
  }) async {
    // Build prompt
    final prompt = _buildDefinitionPrompt(word, language, useNativeLanguage);
    
    // Call LLM
    final response = await _llm.generate(prompt);
    if (response == null || response.isEmpty) {
      throw Exception('Failed to generate definition');
    }
    
    // Parse response (simple text, no suggestions for definitions)
    final definition = response.trim();
    
    // Check if definition already exists
    final db = await _db.database;
    final existing = await db.query(
      'word_definitions',
      where: 'imported_content_id = ?',
      whereArgs: [importedContentId],
    );
    
    final now = DateTime.now().toIso8601String();
    int id;
    
    if (existing.isNotEmpty) {
      // Update existing definition
      id = existing.first['id'] as int;
      await _db.updateItem('word_definitions', id, {
        'definition': definition,
        'definition_language': useNativeLanguage ? 'native' : language,
        'source': 'ai',
        'last_updated': now,
      });
    } else {
      // Create new definition
      id = await _db.insertItem('word_definitions', {
        'imported_content_id': importedContentId,
        'word': word,
        'definition': definition,
        'definition_language': useNativeLanguage ? 'native' : language,
        'source': 'ai',
        'created_at': now,
        'last_updated': now,
        'difficulty_level': 0,
      });
    }
    
    // Return WordDefinition model
    return WordDefinition(
      id: id,
      importedContentId: importedContentId,
      word: word,
      definition: definition,
      definitionLanguage: useNativeLanguage ? 'native' : language,
      source: 'ai',
      createdAt: existing.isNotEmpty 
          ? existing.first['created_at'] as String 
          : now,
      lastUpdated: now,
      difficultyLevel: existing.isNotEmpty
          ? existing.first['difficulty_level'] as int? ?? 0
          : 0,
    );
  }
  
  /// Build definition prompt
  String _buildDefinitionPrompt(
    String word,
    String language,
    bool useNativeLanguage,
  ) {
    final targetLanguage = useNativeLanguage ? 'English' : _getLanguageName(language);
    
    return '''Define the word "$word" in $targetLanguage.

Provide:
1. A clear, concise definition
2. Part of speech (noun, verb, etc.)
3. Any important usage notes

Keep it simple and practical for language learners.''';
  }
  
  /// Get language name from code
  String _getLanguageName(String code) {
    const languageNames = {
      'es': 'Spanish',
      'fr': 'French',
      'de': 'German',
      'it': 'Italian',
      'pt': 'Portuguese',
      'ja': 'Japanese',
      'ko': 'Korean',
      'zh': 'Chinese',
    };
    return languageNames[code] ?? code;
  }
  
  /// Generate example sentences for a word
  Future<List<WordExample>> generateExamples({
    required int wordDefinitionId,
    required String word,
    required String studyLanguage,
    required String nativeLanguage,
    int count = 3,
  }) async {
    // Build prompt
    final prompt = _buildExamplesPrompt(
      word,
      studyLanguage,
      nativeLanguage,
      count,
    );
    
    // Call LLM
    final response = await _llm.generate(prompt);
    if (response == null || response.isEmpty) {
      throw Exception('Failed to generate examples');
    }
    
    // Parse JSON response
    final examples = _parseExamplesResponse(response);
    
    if (examples.isEmpty) {
      throw Exception('No examples generated');
    }
    
    // Update word_definitions.examples field
    await _db.updateItem('word_definitions', wordDefinitionId, {
      'examples': jsonEncode(examples.map((e) => e.toJson()).toList()),
      'last_updated': DateTime.now().toIso8601String(),
    });
    
    return examples;
  }
  
  /// Build examples prompt
  String _buildExamplesPrompt(
    String word,
    String studyLanguage,
    String nativeLanguage,
    int count,
  ) {
    final studyLangName = _getLanguageName(studyLanguage);
    final nativeLangName = _getLanguageName(nativeLanguage);
    
    return '''Provide $count example sentences using the word "$word" in $studyLangName.

For each example:
- Write a natural, practical sentence
- Include $nativeLangName translation
- Use common, everyday contexts

Format as JSON array: [{"sentence": "...", "translation": "..."}]

Return ONLY the JSON array, no other text.''';
  }
  
  /// Parse examples response
  List<WordExample> _parseExamplesResponse(String response) {
    try {
      // Try to find JSON array in response
      final jsonMatch = RegExp(r'\[[\s\S]*\]').firstMatch(response);
      if (jsonMatch == null) {
        throw Exception('No JSON array found in response');
      }
      
      final jsonString = jsonMatch.group(0)!;
      final decoded = jsonDecode(jsonString) as List<dynamic>;
      
      return decoded
          .map((item) => WordExample.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw Exception('Failed to parse examples: $e');
    }
  }
  
  /// Get definition for a word
  Future<WordDefinition?> getDefinition(int importedContentId) async {
    final db = await _db.database;
    final results = await db.query(
      'word_definitions',
      where: 'imported_content_id = ?',
      whereArgs: [importedContentId],
    );
    
    if (results.isEmpty) return null;
    
    return WordDefinition.fromJson(results.first);
  }
  
  /// Update difficulty level
  Future<void> updateDifficulty(int definitionId, int difficulty) async {
    if (difficulty < 0 || difficulty > 5) {
      throw ArgumentError('Difficulty must be between 0 and 5');
    }
    
    await _db.updateItem('word_definitions', definitionId, {
      'difficulty_level': difficulty,
      'last_updated': DateTime.now().toIso8601String(),
    });
  }
}
