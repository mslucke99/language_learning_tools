import 'settings_service.dart';

class Prompts {
  // Word generation prompts
  static const Map<String, Map<String, String>> wordPrompts = {
    'definition': {
      'name': 'Definition',
      'native':
          'Provide a professional language tutor\'s definition of "{word}" in {native_language}. Include: 1. Part of speech. 2. A clear definition. 3. Formality/register (e.g., polite, informal, archaic). 4. A brief "Memory Hook" or etymological note to help remember it.',
      'study':
          'Explain the word "{word}" in {study_language} using very simple language for a beginner. Focus on the most common usage. If the language has formality levels (like Korean), use a standard polite register.',
    },
    'explanation': {
      'name': 'Explanation',
      'native':
          'Explain the usage and nuance of "{word}" in {native_language}. When is this word used vs. its synonyms? Are there regional or social nuances? Provide context on formality/politeness levels if applicable.',
      'study':
          'Describe how to use "{word}" in {study_language} using simple, clear sentences. Show, don\'t just tell, by providing a mini-context where this word is the natural choice.',
    },
    'examples': {
      'name': 'Sample Sentences',
      'native':
          'Provide 3 diverse example sentences for "{word}" in {native_language}. 1. A simple statement. 2. A common question. 3. A sentence showing a unique grammatical property. Highlight the word in **bold**.\n\n**Suggestions**: If any other words in these examples are likely to be difficult for a learner, append a flashcard suggestion at the very end of your response for 1-2 of them in this format: <flashcard word="TERM" context="SENTENCE_WHERE_TERM_APPEARS">BRIEF_DEFINITION</flashcard>',
      'study':
          'Provide 3 simple sentences in {study_language} using "{word}". Include {native_language} translations. Use standard polite forms for Asian languages unless specified otherwise. Highlight the word in **bold**.\n\n**Suggestions**: If any other words in these examples are difficult, append a flashcard suggestion at the very end in this format: <flashcard word="TERM" context="SENTENCE_WHERE_TERM_APPEARS">BRIEF_DEFINITION</flashcard>',
    },
  };

  // Sentence explanation prompts
  static const Map<String, Map<String, String>> sentencePrompts = {
    'grammar': {
      'name': 'Grammar',
      'template':
          'Break down the grammar of this sentence for a language learner: "{sentence}"\n\nIn {language}, explain:\n1. **Morphology**: Break down complex words into roots, suffixes, or particles.\n2. **Syntax**: Explain the word order or sentence structure.\n3. **Key Rules**: Any specific grammar rules (tense, case, aspect) used here.\n\n**Suggestions**: If there is a distinct grammar pattern used, append a grammar suggestion at the very end in this format: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>',
    },
    'vocabulary': {
      'name': 'Vocabulary',
      'template':
          'Analyze the key vocabulary in this sentence: "{sentence}"\n\nList the most important words in {language}, their root forms, and any specific nuances they carry in *this* specific context.',
    },
    'context': {
      'name': 'Context',
      'template':
          'Explain the "vibe" and context of this sentence: "{sentence}"\n\nIn {language}, explain when someone would say this. Is it formal, casual, literary, or historical? What is the speaker\'s intent?',
    },
    'pronunciation': {
      'name': 'Pronunciation',
      'template':
          'Provide pronunciation guidance for: "{sentence}"\n\nFocus on tricky sounds, rhythm, and stress patterns in {study_language}. For languages with pitch-accent or tones, or those like Korean with sound-change rules, explicitly point those out.',
    },
    'all': {
      'name': 'Comprehensive',
      'template':
          'Provide a comprehensive analysis of this sentence for a learner: "{sentence}"\n\nUse {language} to explain:\n1. **Translation**: A natural-sounding translation.\n2. **Literal Breakdown**: A word-for-word mapping if the grammar is very different.\n3. **Grammar & Vocab**: The most critical points to learn from this sentence.\n4. **Usage Tip**: A practical tip on how to use these patterns elsewhere.\n\n**Suggestions**: \n- If there is a distinct grammar pattern, append: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>\n- If there is a difficult word worth studying separately, append: <flashcard word="TERM" context="SENTENCE_WHERE_TERM_APPEARS">BRIEF_DEFINITION</flashcard>',
    },
  };

  // Practice generation prompts
  static const Map<String, Map<String, String>> practicePrompts = {
    'grammar_practice': {
      'name': 'Grammar Practice Generation',
      'template':
          'Create {count} distinct practice sentences in {study_language}. Each sentence must use AT LEAST one of the following grammar patterns:\n{patterns}\n\nProvide the output in JSON format:\n{{\n  "sentences": [\n    {{\n      "sentence": "The sentence in {study_language}",\n      "translation": "The natural translation in {native_language}",\n      "patterns_used": ["Name of pattern used"]\n    }}\n  ]\n}}\nEnsure the sentences are natural and appropriate for a learner who has mastered these patterns.',
    },
  };

  // Writing Composition Lab prompts
  static const Map<String, Map<String, String>> writingPrompts = {
    'generate_topic': {
      'name': 'Generate Topic',
      'template':
          'Suggest a creative writing topic and a short background scenario for a language learner studying {study_language}. The topic should be appropriate for their level and encourage the use of diverse vocabulary and grammar. Provide the response in {native_language}.',
    },
    'grade': {
      'name': 'Grade & Feedback',
      'template':
          'You are a professional language tutor. Grade the following writing in {study_language} about the topic "{topic}":\n\n"{user_writing}"\n\nProvide feedback in {native_language} covering:\n1. **Overall Grade**: A descriptive grade (e.g., A, B+, Beginner, Intermediate).\n2. **Strengths**: What did the user do well?\n3. **Corrections**: Specific grammar or vocabulary mistakes with explanations.\n4. **Natural Phrasing**: How would a native speaker say this more naturally?\n\n**Suggestions**: \n- If the user could benefit from learning a specific new word, append: <flashcard word="TERM" context="SENTENCE_WHERE_TERM_APPEARS">BRIEF_DEFINITION</flashcard>\n- If there is a grammar pattern they should learn, append: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>',
    },
  };

  // Interactive Chat prompts
  static const Map<String, Map<String, String>> chatPrompts = {
    'system_roleplay': {
      'name': 'Roleplay & Analysis',
      'template':
          'You are a friendly language tutor roleplaying as "{persona}" in {study_language}.\nYour goal is to have a natural conversation with the user in {study_language} while analyzing their language usage.\nStrictly follow this XML output format:\n\n<reply>\n  (Write your natural, in-character response here in {study_language}.)\n</reply>\n<feedback>\n  (Provide corrections and feedback on the user\'s *last* message in {native_language}.)\n</feedback>\n<vocab>\n  (List new words from YOUR reply or the user\'s message. Format: <flashcard word="TERM" context="SENTENCE_WHERE_TERM_APPEARS">DEFINITION</flashcard>)\n</vocab>\n<grammar>\n  (Explain any key grammar patterns. Format: <grammar_pattern title="PATTERN">EXPLANATION</grammar_pattern>)\n</grammar>',
    },
  };

  // Exam Practice prompts
  static const Map<String, Map<String, String>> examPrompts = {
    'generate_question': {
      'name': 'Generate Exam Question',
      'template':
          'You are an expert examiner for the {exam_name} ({level}) language exam. Generate a realistic multiple-choice question for the {section} section. The question must follow the exact difficulty and style of the real exam.\n\nStrictly provide the response in this JSON format:\n{{\n  "question": "The question text",\n  "options": ["Option A", "Option B", "Option C", "Option D"],\n  "correct_answer": "The exact string of the correct option",\n  "explanation": "Briefly explain why this is the correct answer in {native_language}"\n}}',
    },
  };

  // Roleplay scenario prompts
  static const Map<String, Map<String, String>> roleplayPrompts = {
    'system_roleplay_scenario': {
      'name': 'Roleplay Scenario',
      'template':
          'You are engaged in a language learning roleplay scenario in {study_language}.\n\n**SCENARIO CONTEXT:**\nSituation: {situation}\nYour role: {user_role}\n\n**ACTIVE CHARACTERS:**\n{characters_description}\n\nStrictly follow this XML output format:\n<characters>\n  <character name="CHARACTER_NAME" role="CHARACTER_ROLE">\n    Character dialogue in {study_language}\n  </character>\n</characters>\n<feedback>\n  Corrections and feedback on the user\'s message in {native_language}.\n</feedback>\n<vocab>\n  List new or important words. Format: <flashcard word="TERM" context="CTX">DEFINITION</flashcard>\n</vocab>\n<grammar>\n  Explain key grammar patterns. Format: <grammar_pattern title="PATTERN">EXPLANATION</grammar_pattern>\n</grammar>',
    },
  };

  static String format(String template, Map<String, String> values) {
    String result = template;
    values.forEach((key, value) {
      result = result.replaceAll('{$key}', value);
    });
    return result;
  }

  static Future<String> getTemplate(
    SettingsService settings,
    String category,
    String promptId,
    String templateType,
  ) async {
    final custom = await settings.getCustomPrompt(
      category,
      promptId,
      templateType,
    );
    if (custom != null && custom.isNotEmpty) {
      return custom;
    }

    // Fallback to defaults
    Map<String, Map<String, String>> prompts;
    switch (category) {
      case 'word':
        prompts = wordPrompts;
        break;
      case 'sentence':
        prompts = sentencePrompts;
        break;
      case 'writing':
        prompts = writingPrompts;
        break;
      case 'chat':
        prompts = chatPrompts;
        break;
      default:
        return '';
    }

    final entry = prompts[promptId];
    if (entry != null) {
      return entry[templateType] ?? '';
    }
    return '';
  }
}
