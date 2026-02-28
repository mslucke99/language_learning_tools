/// Sentence Explanation Service
/// 
/// Generates AI explanations for sentences with embedded suggestions.
/// Supports multiple focus areas (all, grammar, vocabulary, context).

import '../models/sentence_explanation.dart';
import '../models/suggestions.dart';
import 'database_helper.dart';
import 'llm_service.dart';
import 'ai_response_parser.dart';
import 'suggestions_service.dart';

class SentenceExplanationService {
  final DatabaseHelper _db;
  final LLMService _llm;
  final SuggestionsService _suggestionsService;
  
  SentenceExplanationService(
    this._db,
    this._llm,
    this._suggestionsService,
  );
  
  /// Generate explanation for a sentence
  Future<SentenceExplanationResult> generateExplanation({
    required int importedContentId,
    required String sentence,
    required String language,
    String focusArea = 'all',
    bool useNativeLanguage = true,
  }) async {
    // 1. Build prompt based on focus area
    final prompt = _buildExplanationPrompt(
      sentence,
      language,
      focusArea,
      useNativeLanguage,
    );
    
    // 2. Call LLM
    final response = await _llm.generate(prompt);
    if (response == null || response.isEmpty) {
      throw Exception('Failed to generate explanation');
    }
    
    // 3. Parse response for suggestions
    final suggestions = AIResponseParser.parseResponse(response);
    final cleanExplanation = AIResponseParser.cleanResponse(response);
    
    // 4. Save explanation to database
    final now = DateTime.now().toIso8601String();
    final explanationId = await _db.insertItem('sentence_explanations', {
      'imported_content_id': importedContentId,
      'sentence': sentence,
      'explanation': cleanExplanation,
      'explanation_language': useNativeLanguage ? 'native' : language,
      'source': 'ai',
      'focus_area': focusArea,
      'created_at': now,
      'last_updated': now,
    });
    
    // 5. Save suggestions
    await _suggestionsService.storeSentenceSuggestions(
      explanationId,
      suggestions,
    );
    
    // 6. Return result
    return SentenceExplanationResult(
      explanationId: explanationId,
      explanation: cleanExplanation,
      suggestions: suggestions,
    );
  }
  
  /// Get explanation for a sentence
  Future<SentenceExplanation?> getExplanation(int importedContentId) async {
    final db = await _db.database;
    
    final results = await db.query(
      'sentence_explanations',
      where: 'imported_content_id = ?',
      whereArgs: [importedContentId],
      orderBy: 'created_at DESC',
      limit: 1,
    );
    
    if (results.isEmpty) {
      return null;
    }
    
    return SentenceExplanation.fromMap(results.first);
  }
  
  /// Build explanation prompt based on focus area
  String _buildExplanationPrompt(
    String sentence,
    String language,
    String focusArea,
    bool useNativeLanguage,
  ) {
    final explanationLang = useNativeLanguage ? 'English' : _getLanguageName(language);
    final studyLang = _getLanguageName(language);
    
    switch (focusArea) {
      case 'grammar':
        return _buildGrammarPrompt(sentence, studyLang, explanationLang);
      case 'vocabulary':
        return _buildVocabularyPrompt(sentence, studyLang, explanationLang);
      case 'context':
        return _buildContextPrompt(sentence, studyLang, explanationLang);
      case 'all':
      default:
        return _buildComprehensivePrompt(sentence, studyLang, explanationLang);
    }
  }
  
  /// Build comprehensive explanation prompt
  String _buildComprehensivePrompt(
    String sentence,
    String studyLang,
    String explanationLang,
  ) {
    return '''
Explain this $studyLang sentence: "$sentence"

Provide a comprehensive explanation in $explanationLang covering:
1. **Translation**: A natural-sounding translation
2. **Grammar**: Key grammar points and sentence structure
3. **Vocabulary**: Important words and their meanings
4. **Usage**: When and how to use this pattern

**Suggestions**: 
- If there are difficult words worth studying separately, add:
  <flashcard word="WORD" context="$sentence">DEFINITION</flashcard>
- If there are distinct grammar patterns, add:
  <grammar_pattern title="PATTERN_NAME">EXPLANATION</grammar_pattern>

Try to provide at least 2 suggestions if the sentence has sufficient learning points.
''';
  }
  
  /// Build grammar-focused prompt
  String _buildGrammarPrompt(
    String sentence,
    String studyLang,
    String explanationLang,
  ) {
    return '''
Analyze the grammar of this $studyLang sentence: "$sentence"

Focus on:
1. **Sentence Structure**: Break down the grammatical structure
2. **Verb Forms**: Tenses, moods, conjugations
3. **Grammar Rules**: Specific rules being applied
4. **Common Mistakes**: What learners often get wrong

Include grammar pattern suggestions where relevant using:
<grammar_pattern title="PATTERN_NAME">EXPLANATION</grammar_pattern>

Provide your explanation in $explanationLang.
''';
  }
  
  /// Build vocabulary-focused prompt
  String _buildVocabularyPrompt(
    String sentence,
    String studyLang,
    String explanationLang,
  ) {
    return '''
Explain the vocabulary in this $studyLang sentence: "$sentence"

Focus on:
1. **Key Words**: Important vocabulary items
2. **Collocations**: Words that commonly go together
3. **Nuances**: Subtle differences in meaning
4. **Alternatives**: Other ways to express the same idea

Include flashcard suggestions for difficult words using:
<flashcard word="WORD" context="$sentence">DEFINITION</flashcard>

Provide your explanation in $explanationLang.
''';
  }
  
  /// Build context-focused prompt
  String _buildContextPrompt(
    String sentence,
    String studyLang,
    String explanationLang,
  ) {
    return '''
Explain the context and usage of this $studyLang sentence: "$sentence"

Focus on:
1. **When to Use**: Appropriate situations
2. **Formality**: Formal vs informal
3. **Cultural Notes**: Cultural context
4. **Variations**: Regional or situational variations

Include relevant examples and patterns.

Provide your explanation in $explanationLang.
''';
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
}
