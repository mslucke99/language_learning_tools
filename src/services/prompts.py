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
            'Highlight the word in **bold**.\n\n'
            '**Suggestions**: If any other words in these examples are likely to be difficult for a learner, '
            'append a flashcard suggestion at the very end of your response for 1-2 of them in this format: '
            '<flashcard word="TERM">BRIEF_DEFINITION</flashcard>'
        ),
        'study_template': (
            'Provide 3 simple sentences in {study_language} using "{word}". '
            'Include {native_language} translations. Use standard polite forms for Asian languages '
            'unless specified otherwise. Highlight the word in **bold**.\n\n'
            '**Suggestions**: If any other words in these examples are difficult, '
            'append a flashcard suggestion at the very end in this format: '
            '<flashcard word="TERM">BRIEF_DEFINITION</flashcard>\n\n'
            '**Example Output**:\n'
            '1. **사과**를 먹어요. (I eat an apple.)\n'
            '2. 이 **사과**는 빨개요. (This apple is red.)\n'
            '3. **사과**가 맛있어요. (The apple is delicious.)\n\n'
            '<flashcard word="빨개요">To be red</flashcard>'
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
            '3. **Key Rules**: Any specific grammar rules (tense, case, aspect) used here.\n\n'
            '**Suggestions**: If there is a distinct grammar pattern used (e.g., a specific conjugation rule or sentence structure pattern), '
            'append a grammar suggestion at the very end in this format: '
            '<grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>\n\n'
            '**Example Output**:\n'
            'This sentence uses the -고 싶다 pattern to express desire...\n\n'
            '<grammar_pattern title="-고 싶다">Used to express "I want to do..." something.</grammar_pattern>'
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
            '4. **Usage Tip**: A practical tip on how to use these patterns elsewhere.\n\n'
            '**Suggestions**: \n'
            '- If there is a distinct grammar pattern, append: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>\n'
            '- If there is a difficult word worth studying separately, append: <flashcard word="TERM">BRIEF_DEFINITION</flashcard>\n\n'
            '**Example Output**:\n'
            '1. Translation: ...\n'
            '2. Literal Breakdown: ...\n\n'
            '<grammar_pattern title="Subject Particles">Used to mark the subject...</grammar_pattern>\n'
            '<flashcard word="친구">Friend</flashcard>'
        ),
    }
}
# Writing Composition Lab prompts
WRITING_PROMPTS = {
    'generate_topic': {
        'name': 'Generate Topic',
        'template': (
            'Suggest a creative writing topic and a short background scenario for a language learner studying {study_language}. '
            'The topic should be appropriate for their level and encourage the use of diverse vocabulary and grammar. '
            'Provide the response in {native_language}.'
        ),
    },
    'grade': {
        'name': 'Grade & Feedback',
        'template': (
            'You are a professional language tutor. Grade the following writing in {study_language} about the topic "{topic}":\n\n'
            '"{user_writing}"\n\n'
            'Provide feedback in {native_language} covering:\n'
            '1. **Overall Grade**: A descriptive grade (e.g., A, B+, Beginner, Intermediate).\n'
            '2. **Strengths**: What did the user do well?\n'
            '3. **Corrections**: Specific grammar or vocabulary mistakes with explanations.\n'
            '4. **Natural Phrasing**: How would a native speaker say this more naturally?\n\n'
            '**Suggestions**: \n'
            '- If the user could benefit from learning a specific new word used in your feedback or relevant to the topic, '
            'append: <flashcard word="TERM">BRIEF_DEFINITION</flashcard>\n'
            '- If there is a grammar pattern they should learn or that they misused, '
            'append: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>'
        ),
    }
}

# Interactive Chat prompts
CHAT_PROMPTS = {
    'system_roleplay': {
        'name': 'Roleplay & Analysis',
        'template': (
            'You are a friendly language tutor roleplaying as "{persona}" in {study_language}.\n'
            'Your goal is to have a natural conversation with the user in {study_language} while analyzing their language usage.\n'
            'Strictly follow this XML output format:\n\n'
            '<reply>\n'
            '  (Write your natural, in-character response here in {study_language}.)\n'
            '</reply>\n'
            '<feedback>\n'
            '  (Provide corrections and feedback on the user\'s *last* message in {native_language}. '
            'Be encouraging but precise.)\n'
            '</feedback>\n'
            '<vocab>\n'
            '  (List new words from YOUR reply or the user\'s message that are worth studying. '
            'Format: <flashcard word="TERM">DEFINITION</flashcard>)\n'
            '</vocab>\n'
            '<grammar>\n'
            '  (Explain any key grammar patterns used in the conversation. '
            'Format: <grammar_pattern title="PATTERN">EXPLANATION</grammar_pattern>)\n'
            '</grammar>\n\n'
            'Topic: {topic}\n'
            'User Native Language: {native_language}\n'
            'Target Language: {study_language}\n'
            'Begin the conversation or continue it naturally.'
        ),
    }
}
