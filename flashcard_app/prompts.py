"""
Default prompts for AI-powered generation
Can be customized by users in the settings
"""

# Word generation prompts
WORD_PROMPTS = {
    'definition': {
        'name': 'Definition',
        'native_template': (
            'Provide a professional language tutor\'s definition of "{word}" in {native_language}. '
            'Include: 1. Part of speech. 2. A clear definition. 3. Formality/register (e.g., polite, informal, archaic). '
            '4. A brief "Memory Hook" or etymological note to help remember it.'
        ),
        'study_template': (
            'Explain the word "{word}" in {study_language} using very simple language for a beginner. '
            'Focus on the most common usage. If the language has formality levels (like Korean), '
            'use a standard polite register.'
        ),
    },
    'explanation': {
        'name': 'Explanation',
        'native_template': (
            'Explain the usage and nuance of "{word}" in {native_language}. '
            'When is this word used vs. its synonyms? Are there regional or social nuances? '
            'Provide context on formality/politeness levels if applicable.'
        ),
        'study_template': (
            'Describe how to use "{word}" in {study_language} using simple, clear sentences. '
            'Show, don\'t just tell, by providing a mini-context where this word is the natural choice.'
        ),
    },
    'examples': {
        'name': 'Sample Sentences',
        'native_template': (
            'Provide 3 diverse example sentences for "{word}" in {native_language}. '
            '1. A simple statement. 2. A common question. 3. A sentence showing a unique grammatical property. '
            'Highlight the word in **bold**.'
        ),
        'study_template': (
            'Provide 3 simple sentences in {study_language} using "{word}". '
            'Include {native_language} translations. Use standard polite forms for Asian languages '
            'unless specified otherwise. Highlight the word in **bold**.'
        ),
    }
}

# Sentence explanation prompts
SENTENCE_PROMPTS = {
    'grammar': {
        'name': 'Grammar',
        'template': (
            'Break down the grammar of this sentence for a language learner: "{sentence}"\n\n'
            'In {language}, explain:\n'
            '1. **Morphology**: Break down complex words into roots, suffixes, or particles (especially important for Korean or Biblical languages).\n'
            '2. **Syntax**: Explain the word order or sentence structure.\n'
            '3. **Key Rules**: Any specific grammar rules (tense, case, aspect) used here.'
        ),
    },
    'vocabulary': {
        'name': 'Vocabulary',
        'template': (
            'Analyze the key vocabulary in this sentence: "{sentence}"\n\n'
            'List the most important words in {language}, their root forms, '
            'and any specific nuances they carry in *this* specific context.'
        ),
    },
    'context': {
        'name': 'Context',
        'template': (
            'Explain the "vibe" and context of this sentence: "{sentence}"\n\n'
            'In {language}, explain when someone would say this. Is it formal, casual, '
            'literary, or historical? What is the speaker\'s intent?'
        ),
    },
    'pronunciation': {
        'name': 'Pronunciation',
        'template': (
            'Provide pronunciation guidance for: "{sentence}"\n\n'
            'Focus on tricky sounds, rhythm, and stress patterns in {study_language}. '
            'For languages with pitch-accent or tones, or those like Korean with sound-change rules, '
            'explicitly point those out.'
        ),
    },
    'all': {
        'name': 'Comprehensive',
        'template': (
            'Provide a comprehensive analysis of this sentence for a learner: "{sentence}"\n\n'
            'Use {language} to explain:\n'
            '1. **Translation**: A natural-sounding translation.\n'
            '2. **Literal Breakdown**: A word-for-word mapping if the grammar is very different.\n'
            '3. **Grammar & Vocab**: The most critical points to learn from this sentence.\n'
            '4. **Usage Tip**: A practical tip on how to use these patterns elsewhere.'
        ),
    }
}
