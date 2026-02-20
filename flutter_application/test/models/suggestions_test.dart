import 'package:flutter_test/flutter_test.dart';
import 'package:proficiency_suites/models/suggestions.dart';

void main() {
  group('FlashcardSuggestion', () {
    test('creates instance with required fields', () {
      final flashcard = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word in Spanish',
      );
      
      expect(flashcard.word, 'palabra');
      expect(flashcard.definition, 'word in Spanish');
      expect(flashcard.context, isNull);
    });
    
    test('creates instance with optional context', () {
      final flashcard = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word in Spanish',
        context: 'Esta es una palabra.',
      );
      
      expect(flashcard.context, 'Esta es una palabra.');
    });
    
    test('converts to JSON correctly', () {
      final flashcard = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word in Spanish',
        context: 'context here',
      );
      
      final json = flashcard.toJson();
      
      expect(json['word'], 'palabra');
      expect(json['definition'], 'word in Spanish');
      expect(json['context'], 'context here');
    });
    
    test('converts to JSON without context', () {
      final flashcard = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word in Spanish',
      );
      
      final json = flashcard.toJson();
      
      expect(json['word'], 'palabra');
      expect(json['definition'], 'word in Spanish');
      expect(json.containsKey('context'), false);
    });
    
    test('creates from JSON correctly', () {
      final json = {
        'word': 'palabra',
        'definition': 'word in Spanish',
        'context': 'context here',
      };
      
      final flashcard = FlashcardSuggestion.fromJson(json);
      
      expect(flashcard.word, 'palabra');
      expect(flashcard.definition, 'word in Spanish');
      expect(flashcard.context, 'context here');
    });
    
    test('creates from JSON without context', () {
      final json = {
        'word': 'palabra',
        'definition': 'word in Spanish',
      };
      
      final flashcard = FlashcardSuggestion.fromJson(json);
      
      expect(flashcard.word, 'palabra');
      expect(flashcard.definition, 'word in Spanish');
      expect(flashcard.context, isNull);
    });
    
    test('equality works correctly', () {
      final flashcard1 = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word',
      );
      final flashcard2 = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word',
      );
      final flashcard3 = FlashcardSuggestion(
        word: 'different',
        definition: 'word',
      );
      
      expect(flashcard1, equals(flashcard2));
      expect(flashcard1, isNot(equals(flashcard3)));
    });
    
    test('hashCode works correctly', () {
      final flashcard1 = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word',
      );
      final flashcard2 = FlashcardSuggestion(
        word: 'palabra',
        definition: 'word',
      );
      
      expect(flashcard1.hashCode, equals(flashcard2.hashCode));
    });
  });
  
  group('GrammarSuggestion', () {
    test('creates instance correctly', () {
      final grammar = GrammarSuggestion(
        title: 'Present Tense',
        explanation: 'Used for current actions',
      );
      
      expect(grammar.title, 'Present Tense');
      expect(grammar.explanation, 'Used for current actions');
    });
    
    test('converts to JSON correctly', () {
      final grammar = GrammarSuggestion(
        title: 'Present Tense',
        explanation: 'Used for current actions',
      );
      
      final json = grammar.toJson();
      
      expect(json['title'], 'Present Tense');
      expect(json['explanation'], 'Used for current actions');
    });
    
    test('creates from JSON correctly', () {
      final json = {
        'title': 'Present Tense',
        'explanation': 'Used for current actions',
      };
      
      final grammar = GrammarSuggestion.fromJson(json);
      
      expect(grammar.title, 'Present Tense');
      expect(grammar.explanation, 'Used for current actions');
    });
    
    test('equality works correctly', () {
      final grammar1 = GrammarSuggestion(
        title: 'Present Tense',
        explanation: 'explanation',
      );
      final grammar2 = GrammarSuggestion(
        title: 'Present Tense',
        explanation: 'explanation',
      );
      final grammar3 = GrammarSuggestion(
        title: 'Past Tense',
        explanation: 'explanation',
      );
      
      expect(grammar1, equals(grammar2));
      expect(grammar1, isNot(equals(grammar3)));
    });
  });
  
  group('Suggestions', () {
    test('creates empty suggestions by default', () {
      final suggestions = Suggestions();
      
      expect(suggestions.flashcards, isEmpty);
      expect(suggestions.grammar, isEmpty);
      expect(suggestions.isEmpty, true);
      expect(suggestions.isNotEmpty, false);
      expect(suggestions.totalCount, 0);
    });
    
    test('creates suggestions with flashcards', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
          FlashcardSuggestion(word: 'word2', definition: 'def2'),
        ],
      );
      
      expect(suggestions.flashcards.length, 2);
      expect(suggestions.grammar, isEmpty);
      expect(suggestions.isEmpty, false);
      expect(suggestions.isNotEmpty, true);
      expect(suggestions.totalCount, 2);
    });
    
    test('creates suggestions with grammar patterns', () {
      final suggestions = Suggestions(
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
        ],
      );
      
      expect(suggestions.flashcards, isEmpty);
      expect(suggestions.grammar.length, 1);
      expect(suggestions.totalCount, 1);
    });
    
    test('creates suggestions with both types', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
        ],
      );
      
      expect(suggestions.flashcards.length, 1);
      expect(suggestions.grammar.length, 1);
      expect(suggestions.totalCount, 2);
    });
    
    test('converts to JSON correctly', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
        ],
      );
      
      final json = suggestions.toJson();
      
      expect(json['flashcards'], isList);
      expect(json['flashcards'].length, 1);
      expect(json['grammar'], isList);
      expect(json['grammar'].length, 1);
    });
    
    test('creates from JSON correctly', () {
      final json = {
        'flashcards': [
          {'word': 'word1', 'definition': 'def1'},
        ],
        'grammar': [
          {'title': 'pattern1', 'explanation': 'exp1'},
        ],
      };
      
      final suggestions = Suggestions.fromJson(json);
      
      expect(suggestions.flashcards.length, 1);
      expect(suggestions.flashcards[0].word, 'word1');
      expect(suggestions.grammar.length, 1);
      expect(suggestions.grammar[0].title, 'pattern1');
    });
    
    test('creates from JSON with missing fields', () {
      final json = <String, dynamic>{};
      
      final suggestions = Suggestions.fromJson(json);
      
      expect(suggestions.flashcards, isEmpty);
      expect(suggestions.grammar, isEmpty);
    });
    
    test('converts to JSON string correctly', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
      );
      
      final jsonString = suggestions.toJsonString();
      
      expect(jsonString, isA<String>());
      expect(jsonString, contains('word1'));
      expect(jsonString, contains('def1'));
    });
    
    test('creates from JSON string correctly', () {
      final jsonString = '{"flashcards":[{"word":"word1","definition":"def1"}],"grammar":[]}';
      
      final suggestions = Suggestions.fromJsonString(jsonString);
      
      expect(suggestions.flashcards.length, 1);
      expect(suggestions.flashcards[0].word, 'word1');
    });
    
    test('handles invalid JSON string gracefully', () {
      final jsonString = 'invalid json {{{';
      
      final suggestions = Suggestions.fromJsonString(jsonString);
      
      expect(suggestions.isEmpty, true);
    });
    
    test('equality works correctly', () {
      final suggestions1 = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
      );
      final suggestions2 = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
      );
      final suggestions3 = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word2', definition: 'def2'),
        ],
      );
      
      expect(suggestions1, equals(suggestions2));
      expect(suggestions1, isNot(equals(suggestions3)));
    });
    
    test('toString works correctly', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(word: 'word1', definition: 'def1'),
        ],
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
        ],
      );
      
      final string = suggestions.toString();
      
      expect(string, contains('flashcards: 1'));
      expect(string, contains('grammar: 1'));
    });
    
    test('handles special characters in JSON serialization', () {
      final suggestions = Suggestions(
        flashcards: [
          FlashcardSuggestion(
            word: 'café',
            definition: 'coffee with "quotes" and \'apostrophes\'',
            context: 'Line 1\nLine 2',
          ),
        ],
      );
      
      final jsonString = suggestions.toJsonString();
      final restored = Suggestions.fromJsonString(jsonString);
      
      expect(restored.flashcards[0].word, 'café');
      expect(restored.flashcards[0].definition, contains('quotes'));
      expect(restored.flashcards[0].context, contains('\n'));
    });
    
    test('round-trip JSON serialization preserves data', () {
      final original = Suggestions(
        flashcards: [
          FlashcardSuggestion(
            word: 'word1',
            definition: 'def1',
            context: 'context1',
          ),
          FlashcardSuggestion(word: 'word2', definition: 'def2'),
        ],
        grammar: [
          GrammarSuggestion(title: 'pattern1', explanation: 'exp1'),
        ],
      );
      
      final jsonString = original.toJsonString();
      final restored = Suggestions.fromJsonString(jsonString);
      
      expect(restored, equals(original));
    });
  });
}
