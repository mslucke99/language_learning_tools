import 'package:flutter_test/flutter_test.dart';
import 'package:proficiency_suites/services/ai_response_parser.dart';
import 'package:proficiency_suites/models/suggestions.dart';

void main() {
  group('AIResponseParser', () {
    group('parseResponse', () {
      test('parses response with flashcard tags', () {
        const response = '''
This is a great explanation!

<flashcard word="palabra">word in Spanish</flashcard>
<flashcard word="difícil">difficult</flashcard>
''';

        final suggestions = AIResponseParser.parseResponse(response);

        expect(suggestions.flashcards.length, 2);
        expect(suggestions.flashcards[0].word, 'palabra');
        expect(suggestions.flashcards[0].definition, 'word in Spanish');
        expect(suggestions.flashcards[1].word, 'difícil');
        expect(suggestions.flashcards[1].definition, 'difficult');
        expect(suggestions.grammar.length, 0);
      });

      test('parses response with grammar tags', () {
        const response = '''
Grammar explanation here.

<grammar_pattern title="Present Tense">Used for current actions</grammar_pattern>
<grammar_pattern title="Subjunctive">Used for wishes and doubts</grammar_pattern>
''';

        final suggestions = AIResponseParser.parseResponse(response);

        expect(suggestions.grammar.length, 2);
        expect(suggestions.grammar[0].title, 'Present Tense');
        expect(suggestions.grammar[0].explanation, 'Used for current actions');
        expect(suggestions.grammar[1].title, 'Subjunctive');
        expect(suggestions.grammar[1].explanation, 'Used for wishes and doubts');
        expect(suggestions.flashcards.length, 0);
      });

      test('parses response with both flashcard and grammar tags', () {
        const response = '''
Comprehensive explanation.

<flashcard word="querer">to want</flashcard>
<grammar_pattern title="Querer + Infinitive">Express desire with querer + infinitive verb</grammar_pattern>
''';

        final suggestions = AIResponseParser.parseResponse(response);

        expect(suggestions.flashcards.length, 1);
        expect(suggestions.grammar.length, 1);
        expect(suggestions.totalCount, 2);
      });

      test('parses response with no tags', () {
        const response = 'Just a plain explanation with no suggestions.';

        final suggestions = AIResponseParser.parseResponse(response);

        expect(suggestions.isEmpty, true);
        expect(suggestions.flashcards.length, 0);
        expect(suggestions.grammar.length, 0);
      });

      test('parses flashcard with context attribute', () {
        const response = '''
<flashcard word="biblioteca" context="Quiero ir a la biblioteca">library</flashcard>
''';

        final suggestions = AIResponseParser.parseResponse(response);

        expect(suggestions.flashcards.length, 1);
        expect(suggestions.flashcards[0].word, 'biblioteca');
        expect(suggestions.flashcards[0].definition, 'library');
        expect(suggestions.flashcards[0].context, 'Quiero ir a la biblioteca');
      });
    });

    group('extractFlashcards', () {
      test('extracts multiple flashcards', () {
        const text = '''
<flashcard word="uno">one</flashcard>
<flashcard word="dos">two</flashcard>
<flashcard word="tres">three</flashcard>
''';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 3);
        expect(flashcards[0].word, 'uno');
        expect(flashcards[1].word, 'dos');
        expect(flashcards[2].word, 'tres');
      });

      test('handles single quotes in attributes', () {
        const text = "<flashcard word='palabra'>word</flashcard>";

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].word, 'palabra');
      });

      test('handles double quotes in attributes', () {
        const text = '<flashcard word="palabra">word</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].word, 'palabra');
      });

      test('handles malformed XML - missing closing tag', () {
        const text = '<flashcard word="palabra">word';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 0);
      });

      test('handles malformed XML - missing word attribute', () {
        const text = '<flashcard>word</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 0);
      });

      test('handles special characters in word', () {
        const text = '<flashcard word="café">coffee</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].word, 'café');
      });

      test('handles special characters in definition', () {
        const text = '<flashcard word="test">It\'s a "test"</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].definition, 'It\'s a "test"');
      });

      test('handles XML entities in content', () {
        const text = '<flashcard word="test">&lt;definition&gt; &amp; more</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].definition, '<definition> & more');
      });

      test('handles multiline definitions', () {
        const text = '''
<flashcard word="test">This is a
multiline
definition</flashcard>
''';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].definition, contains('multiline'));
      });

      test('handles empty word attribute', () {
        const text = '<flashcard word="">definition</flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 0);
      });

      test('handles empty definition', () {
        const text = '<flashcard word="test"></flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 0);
      });

      test('handles whitespace in attributes and content', () {
        const text = '<flashcard word="  palabra  ">  word  </flashcard>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].word, 'palabra');
        expect(flashcards[0].definition, 'word');
      });

      test('handles case-insensitive tags', () {
        const text = '<FLASHCARD WORD="test">definition</FLASHCARD>';

        final flashcards = AIResponseParser.extractFlashcards(text);

        expect(flashcards.length, 1);
        expect(flashcards[0].word, 'test');
      });
    });

    group('extractGrammarPatterns', () {
      test('extracts multiple grammar patterns', () {
        const text = '''
<grammar_pattern title="Pattern 1">Explanation 1</grammar_pattern>
<grammar_pattern title="Pattern 2">Explanation 2</grammar_pattern>
''';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 2);
        expect(patterns[0].title, 'Pattern 1');
        expect(patterns[0].explanation, 'Explanation 1');
        expect(patterns[1].title, 'Pattern 2');
        expect(patterns[1].explanation, 'Explanation 2');
      });

      test('handles single quotes in attributes', () {
        const text = "<grammar_pattern title='Present Tense'>explanation</grammar_pattern>";

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 1);
        expect(patterns[0].title, 'Present Tense');
      });

      test('handles malformed XML - missing closing tag', () {
        const text = '<grammar_pattern title="Test">explanation';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 0);
      });

      test('handles malformed XML - missing title attribute', () {
        const text = '<grammar_pattern>explanation</grammar_pattern>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 0);
      });

      test('handles multiline explanations', () {
        const text = '''
<grammar_pattern title="Test">This is a
multiline
explanation</grammar_pattern>
''';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 1);
        expect(patterns[0].explanation, contains('multiline'));
      });

      test('handles XML entities in content', () {
        const text = '<grammar_pattern title="Test">&lt;example&gt; &amp; more</grammar_pattern>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 1);
        expect(patterns[0].explanation, '<example> & more');
      });

      test('handles empty title attribute', () {
        const text = '<grammar_pattern title="">explanation</grammar_pattern>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 0);
      });

      test('handles empty explanation', () {
        const text = '<grammar_pattern title="Test"></grammar_pattern>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 0);
      });

      test('handles whitespace in attributes and content', () {
        const text = '<grammar_pattern title="  Present Tense  ">  explanation  </grammar_pattern>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 1);
        expect(patterns[0].title, 'Present Tense');
        expect(patterns[0].explanation, 'explanation');
      });

      test('handles case-insensitive tags', () {
        const text = '<GRAMMAR_PATTERN TITLE="test">explanation</GRAMMAR_PATTERN>';

        final patterns = AIResponseParser.extractGrammarPatterns(text);

        expect(patterns.length, 1);
        expect(patterns[0].title, 'test');
      });
    });

    group('cleanResponse', () {
      test('removes flashcard tags from text', () {
        const text = '''
This is an explanation.

<flashcard word="palabra">word</flashcard>

More explanation here.
''';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned, contains('This is an explanation.'));
        expect(cleaned, contains('More explanation here.'));
        expect(cleaned, isNot(contains('<flashcard')));
        expect(cleaned, isNot(contains('palabra')));
      });

      test('removes grammar_pattern tags from text', () {
        const text = '''
Grammar explanation.

<grammar_pattern title="Present Tense">Used for current actions</grammar_pattern>

More text.
''';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned, contains('Grammar explanation.'));
        expect(cleaned, contains('More text.'));
        expect(cleaned, isNot(contains('<grammar_pattern')));
        expect(cleaned, isNot(contains('Present Tense')));
      });

      test('removes both types of tags', () {
        const text = '''
Explanation.

<flashcard word="test">definition</flashcard>
<grammar_pattern title="Pattern">explanation</grammar_pattern>

End.
''';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned, contains('Explanation.'));
        expect(cleaned, contains('End.'));
        expect(cleaned, isNot(contains('<flashcard')));
        expect(cleaned, isNot(contains('<grammar_pattern')));
      });

      test('cleans up extra whitespace', () {
        const text = '''
Line 1.


<flashcard word="test">definition</flashcard>



Line 2.
''';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned, contains('Line 1.'));
        expect(cleaned, contains('Line 2.'));
        // Should not have more than 2 consecutive newlines
        expect(cleaned, isNot(contains('\n\n\n')));
      });

      test('returns original text if no tags present', () {
        const text = 'Just plain text with no tags.';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned, text);
      });

      test('handles text with only tags', () {
        const text = '''
<flashcard word="test">definition</flashcard>
<grammar_pattern title="Pattern">explanation</grammar_pattern>
''';

        final cleaned = AIResponseParser.cleanResponse(text);

        expect(cleaned.trim(), isEmpty);
      });
    });

    group('Integration tests', () {
      test('parses realistic AI response', () {
        const response = '''
**Translation**: "I want to go to the library."

**Grammar**: This uses the construction "querer + infinitive" to express desire.
The verb "ir" (to go) is in infinitive form after "quiero".

**Vocabulary**: 
- "quiero" = I want (from querer)
- "ir" = to go
- "biblioteca" = library

**Usage**: This is a very common pattern for expressing what you want to do.

<flashcard word="querer" context="Quiero ir a la biblioteca">to want, to love</flashcard>
<flashcard word="biblioteca" context="Quiero ir a la biblioteca">library</flashcard>
<grammar_pattern title="Querer + Infinitive">Use "querer" + infinitive verb to express desire or intention. Example: Quiero comer (I want to eat)</grammar_pattern>
''';

        final suggestions = AIResponseParser.parseResponse(response);
        final cleaned = AIResponseParser.cleanResponse(response);

        // Check suggestions
        expect(suggestions.flashcards.length, 2);
        expect(suggestions.grammar.length, 1);
        
        expect(suggestions.flashcards[0].word, 'querer');
        expect(suggestions.flashcards[0].context, 'Quiero ir a la biblioteca');
        
        expect(suggestions.grammar[0].title, 'Querer + Infinitive');
        expect(suggestions.grammar[0].explanation, contains('desire or intention'));

        // Check cleaned text
        expect(cleaned, contains('**Translation**'));
        expect(cleaned, contains('**Grammar**'));
        expect(cleaned, isNot(contains('<flashcard')));
        expect(cleaned, isNot(contains('<grammar_pattern')));
      });

      test('handles response with no suggestions gracefully', () {
        const response = '''
This is just a simple explanation without any embedded suggestions.
It provides information but doesn't include flashcards or grammar patterns.
''';

        final suggestions = AIResponseParser.parseResponse(response);
        final cleaned = AIResponseParser.cleanResponse(response);

        expect(suggestions.isEmpty, true);
        expect(cleaned, response.trim());
      });
    });
  });
}
