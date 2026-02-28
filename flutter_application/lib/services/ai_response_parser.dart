/// AI Response Parser Service
/// 
/// Parses AI-generated responses to extract embedded suggestions in XML format.
/// Supports flashcard and grammar pattern tags.
/// 
/// Example input:
/// ```
/// This is a great explanation!
/// 
/// <flashcard word="palabra">word in Spanish</flashcard>
/// <grammar_pattern title="Present Tense">Used for current actions</grammar_pattern>
/// ```
/// 
/// Example output:
/// ```dart
/// Suggestions(
///   flashcards: [FlashcardSuggestion(word: 'palabra', definition: 'word in Spanish')],
///   grammar: [GrammarSuggestion(title: 'Present Tense', explanation: 'Used for current actions')]
/// )
/// ```

import '../models/suggestions.dart';

class AIResponseParser {
  /// Parse AI response text and extract all suggestions
  static Suggestions parseResponse(String responseText) {
    final flashcards = extractFlashcards(responseText);
    final grammar = extractGrammarPatterns(responseText);
    
    return Suggestions(
      flashcards: flashcards,
      grammar: grammar,
    );
  }
  
  /// Extract flashcard tags from text
  /// 
  /// Matches patterns like:
  /// - <flashcard word="palabra">definition</flashcard>
  /// - <flashcard word="palabra" context="sentence">definition</flashcard>
  static List<FlashcardSuggestion> extractFlashcards(String text) {
    final flashcards = <FlashcardSuggestion>[];
    
    // Pattern to match flashcard tags with optional context attribute
    // Handles both single and double quotes
    final doubleQuotePattern = RegExp(
      r'<flashcard\s+word="([^"]+)"(?:\s+context="([^"]+)")?\s*>(.+?)</flashcard>',
      caseSensitive: false,
      dotAll: true,
    );
    
    final singleQuotePattern = RegExp(
      r"<flashcard\s+word='([^']+)'(?:\s+context='([^']+)')?\s*>(.+?)</flashcard>",
      caseSensitive: false,
      dotAll: true,
    );
    
    // Try both patterns
    for (final pattern in [doubleQuotePattern, singleQuotePattern]) {
      final matches = pattern.allMatches(text);
      
      for (final match in matches) {
        try {
          final word = match.group(1)?.trim() ?? '';
          final context = match.group(2)?.trim();
          final definition = match.group(3)?.trim() ?? '';
          
          if (word.isNotEmpty && definition.isNotEmpty) {
            flashcards.add(FlashcardSuggestion(
              word: _unescapeXml(word),
              definition: _unescapeXml(definition),
              context: context != null && context.isNotEmpty 
                  ? _unescapeXml(context) 
                  : null,
            ));
          }
        } catch (e) {
          // Skip malformed tags
          continue;
        }
      }
    }
    
    return flashcards;
  }
  
  /// Extract grammar pattern tags from text
  /// 
  /// Matches patterns like:
  /// - <grammar_pattern title="Present Tense">explanation</grammar_pattern>
  static List<GrammarSuggestion> extractGrammarPatterns(String text) {
    final patterns = <GrammarSuggestion>[];
    
    // Pattern to match grammar_pattern tags with double quotes
    final doubleQuotePattern = RegExp(
      r'<grammar_pattern\s+title="([^"]+)"\s*>(.+?)</grammar_pattern>',
      caseSensitive: false,
      dotAll: true,
    );
    
    // Pattern to match grammar_pattern tags with single quotes
    final singleQuotePattern = RegExp(
      r"<grammar_pattern\s+title='([^']+)'\s*>(.+?)</grammar_pattern>",
      caseSensitive: false,
      dotAll: true,
    );
    
    // Try both patterns
    for (final pattern in [doubleQuotePattern, singleQuotePattern]) {
      final matches = pattern.allMatches(text);
      
      for (final match in matches) {
        try {
          final title = match.group(1)?.trim() ?? '';
          final explanation = match.group(2)?.trim() ?? '';
          
          if (title.isNotEmpty && explanation.isNotEmpty) {
            patterns.add(GrammarSuggestion(
              title: _unescapeXml(title),
              explanation: _unescapeXml(explanation),
            ));
          }
        } catch (e) {
          // Skip malformed tags
          continue;
        }
      }
    }
    
    return patterns;
  }
  
  /// Remove all suggestion tags from text, leaving clean content
  /// 
  /// Useful for displaying the main explanation without embedded tags.
  static String cleanResponse(String text) {
    String cleaned = text;
    
    // Remove flashcard tags with double quotes
    cleaned = cleaned.replaceAll(
      RegExp(
        r'<flashcard\s+word="[^"]*"(?:\s+context="[^"]*")?\s*>.*?</flashcard>',
        caseSensitive: false,
        dotAll: true,
      ),
      '',
    );
    
    // Remove flashcard tags with single quotes
    cleaned = cleaned.replaceAll(
      RegExp(
        r"<flashcard\s+word='[^']*'(?:\s+context='[^']*')?\s*>.*?</flashcard>",
        caseSensitive: false,
        dotAll: true,
      ),
      '',
    );
    
    // Remove grammar_pattern tags with double quotes
    cleaned = cleaned.replaceAll(
      RegExp(
        r'<grammar_pattern\s+title="[^"]*"\s*>.*?</grammar_pattern>',
        caseSensitive: false,
        dotAll: true,
      ),
      '',
    );
    
    // Remove grammar_pattern tags with single quotes
    cleaned = cleaned.replaceAll(
      RegExp(
        r"<grammar_pattern\s+title='[^']*'\s*>.*?</grammar_pattern>",
        caseSensitive: false,
        dotAll: true,
      ),
      '',
    );
    
    // Clean up extra whitespace
    cleaned = cleaned.replaceAll(RegExp(r'\n\s*\n\s*\n'), '\n\n');
    cleaned = cleaned.trim();
    
    return cleaned;
  }
  
  /// Unescape common XML entities
  static String _unescapeXml(String text) {
    return text
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&amp;', '&')
        .replaceAll('&quot;', '"')
        .replaceAll('&apos;', "'");
  }
}
