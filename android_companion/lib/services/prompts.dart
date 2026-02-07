class Prompts {
  static const Map<String, Map<String, String>> wordPrompts = {
    'definition': {
      'native':
          'Provide a professional language tutor\'s definition of "{word}" in {native_language}. Include: 1. Part of speech. 2. A clear definition. 3. Formality/register (e.g., polite, informal, archaic). 4. A brief "Memory Hook" or etymological note to help remember it.',
      'study':
          'Explain the word "{word}" in {study_language} using very simple language for a beginner. Focus on the most common usage.',
    },
  };

  static const Map<String, String> sentencePrompts = {
    'all':
        'Provide a comprehensive analysis of this sentence for a learner: "{sentence}"\n\nUse {language} to explain:\n1. Translation: A natural-sounding translation.\n2. Literal Breakdown: A word-for-word mapping.\n3. Grammar & Vocab: The most critical points.\n4. Usage Tip: A practical tip.',
  };

  static const Map<String, String> chatPrompts = {
    'system_roleplay':
        'You are a friendly language tutor roleplaying as "{persona}" in {study_language}.\nYour goal is to have a natural conversation with the user while analyzing their language usage.\nStrictly follow this XML output format:\n\n<reply>(Your response here)</reply>\n<feedback>(Feedback on the user\'s last message in {native_language})</feedback>\n<vocab><flashcard word="TERM">DEFINITION</flashcard></vocab>\n<grammar><grammar_pattern title="PATTERN">EXPLANATION</grammar_pattern></grammar>',
  };

  static String format(String template, Map<String, String> values) {
    String result = template;
    values.forEach((key, value) {
      result = result.replaceAll('{$key}', value);
    });
    return result;
  }
}
