"""
Default prompts for AI-powered generation
Can be customized by users in the settings
"""

# Word generation prompts
WORD_PROMPTS = {
    'definition': {
        'name': 'Definition',
        'native_template': 'Provide a clear, concise definition of the word "{word}" in {native_language}. Keep it to 1-2 sentences. Include context about common usage.',
        'study_template': 'Explain the word "{word}" in {study_language} using simple, common words that a beginner would understand. Use present tense and active voice. Keep it to 1-2 sentences.',
    },
    'explanation': {
        'name': 'Explanation',
        'native_template': 'Explain how the word "{word}" is used in context in {native_language}. Describe when and where this word is typically used. Keep it to 2-3 sentences.',
        'study_template': 'Explain how and when to use the word "{word}" in {study_language}. Provide practical usage context. Keep it to 2-3 sentences in simple language.',
    },
    'examples': {
        'name': 'Sample Sentences',
        'native_template': 'Provide 3 example sentences using the word "{word}" in {native_language}. Make the sentences diverse and realistic. Format as a numbered list.',
        'study_template': 'Provide 3 example sentences using the word "{word}" in {study_language}. Make them simple and beginner-friendly. Format as a numbered list (1. 2. 3.)',
    }
}

# Sentence explanation prompts
SENTENCE_PROMPTS = {
    'grammar': {
        'name': 'Grammar',
        'template': 'Explain the grammar structures in this sentence in {language}:\n"{sentence}"\nFocus on tense, verb forms, and sentence structure. Keep it concise.',
    },
    'vocabulary': {
        'name': 'Vocabulary',
        'template': 'Explain the key vocabulary words in this sentence in {language}:\n"{sentence}"\nFocus on word meanings and usage. Keep it concise.',
    },
    'context': {
        'name': 'Context',
        'template': 'Explain the context and meaning of this sentence in {language}:\n"{sentence}"\nFocus on what the sentence means and when it would be used. Keep it concise.',
    },
    'pronunciation': {
        'name': 'Pronunciation',
        'template': 'Provide pronunciation guidance for the key words in this sentence in {study_language}:\n"{sentence}"\nInclude stress patterns and any tricky sounds.',
    },
    'all': {
        'name': 'Comprehensive',
        'template': 'Provide a comprehensive explanation of this sentence in {language}:\n"{sentence}"\nInclude grammar, vocabulary, and context. Keep it concise (3-4 sentences).',
    }
}
