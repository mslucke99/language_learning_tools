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
            '<flashcard word="TERM">BRIEF_DEFINITION</flashcard>\n\n'
            '**Example 1 (with suggestions):**\n'
            '1. The **ephemeral** beauty of cherry blossoms captivates visitors.\n'
            '2. Is this feeling **ephemeral** or lasting?\n'
            '3. Their **ephemeral** success faded quickly.\n\n'
            '<flashcard word="captivates">To attract and hold interest</flashcard>\n\n'
            '**Example 2 (no suggestions - basic words):**\n'
            '1. I **walk** to school every day.\n'
            '2. Do you **walk** or take the bus?\n'
            '3. They **walk** together in the park.\n'
            '(No suggestions needed - common vocabulary)'
        ),
        'study_template': (
            'Provide 3 simple sentences in {study_language} using "{word}". '
            'Include {native_language} translations. Use standard polite forms for Asian languages '
            'unless specified otherwise. Highlight the word in **bold**.\n\n'
            '**Suggestions**: If any other words in these examples are difficult, '
            'append a flashcard suggestion at the very end in this format: '
            '<flashcard word="TERM">BRIEF_DEFINITION</flashcard>\n\n'
            '**Example 1 (with suggestion):**\n'
            '1. **사과**를 먹어요. (I eat an apple.)\n'
            '2. 이 **사과**는 빨개요. (This apple is red.)\n'
            '3. **사과**가 맛있어요. (The apple is delicious.)\n\n'
            '<flashcard word="빨개요">To be red (adjective form)</flashcard>\n\n'
            '**Example 2 (no suggestions - basic words):**\n'
            '1. Yo **como** pan. (I eat bread.)\n'
            '2. ¿Tú **comes** frutas? (Do you eat fruits?)\n'
            '3. Ellos **comen** en casa. (They eat at home.)\n'
            '(No suggestions - "comer" conjugations are fundamental)'
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
            '**Example 1 (with grammar pattern):**\n'
            '**Morphology**: 먹 (eat) + 고 (and) + 싶다 (want to)\n'
            '**Syntax**: Subject + Object + Verb-고 싶다 pattern\n'
            '**Key Rules**: The -고 싶다 pattern expresses desire to do an action.\n\n'
            '<grammar_pattern title="-고 싶다 Pattern">Attach -고 싶다 to verb stems to express "I want to [verb]"</grammar_pattern>\n\n'
            '**Example 2 (complex - with both):**\n'
            '**Morphology**: 친구 (friend) + 가 (subject) + 준 (gave-past) + 책 (book)\n'
            '**Syntax**: Relative clause "친구가 준" modifies "책"\n'
            '**Key Rules**: Past tense modifier -(으)ㄴ creates relative clauses.\n\n'
            '<grammar_pattern title="Relative Clauses">Use verb stem + -(으)ㄴ/는 to modify nouns</grammar_pattern>\n'
            '<flashcard word="주다">To give</flashcard>\n\n'
            '**Example 3 (simple - no suggestions):**\n'
            '**Morphology**: Simple present tense\n'
            '**Syntax**: Standard SVO order\n'
            '**Key Rules**: Basic present tense conjugation\n'
            '(No suggestions - fundamental grammar)'
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
            '**Example Output:**\n'
            '**Translation**: "I want to go to the library."\n'
            '**Literal Breakdown**: 나는 (I) + 도서관에 (to library) + 가고 싶어요 (want to go)\n'
            '**Grammar & Vocab**: Uses -고 싶다 pattern for expressing desire. 도서관 means library.\n'
            '**Usage Tip**: Replace 가다 with any verb to express "want to [verb]".\n\n'
            '<grammar_pattern title="-고 싶다 Desire Pattern">Attach to verb stems: 먹고 싶다 (want to eat), 자고 싶다 (want to sleep)</grammar_pattern>\n'
            '<flashcard word="도서관">Library</flashcard>'
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
            'append: <grammar_pattern title="PATTERN_NAME">BRIEF_EXPLANATION</grammar_pattern>\n\n'
            '**Example Output:**\n'
            '**Overall Grade**: B+ (Intermediate)\n\n'
            '**Strengths**: Good vocabulary variety, clear topic sentences, nice use of connectors.\n\n'
            '**Corrections**:\n'
            '- "나는 학교에 갔어요" → In casual writing, the subject is often omitted: "학교에 갔어요"\n'
            '- "재미있었어요" is correct, but "즐거웠어요" sounds more natural for personal experiences\n\n'
            '**Natural Phrasing**: Instead of "나는 친구와 놀았어요", try "친구랑 놀았어요" (랑 is more casual than 와)\n\n'
            '<grammar_pattern title="Subject Omission in Korean">Korean often omits obvious subjects in casual speech and writing</grammar_pattern>\n'
            '<flashcard word="즐겁다">To be enjoyable/pleasant (experience-focused, more natural than 재미있다 for personal experiences)</flashcard>'
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
            '**Example Conversation:**\n'
            'User: "안녕하세요! 오늘 날씨가 좋아요."\n\n'
            '<reply>\n'
            '네, 정말 좋네요! 산책하기 딱 좋은 날씨예요. 주말에 뭐 하실 거예요?\n'
            '</reply>\n'
            '<feedback>\n'
            'Great use of 좋아요! Small tip: "날씨가 좋아요" is perfect. You could also say "날씨가 좋네요" for a more observational, gentle tone.\n'
            '</feedback>\n'
            '<vocab>\n'
            '<flashcard word="산책">A walk, stroll</flashcard>\n'
            '<flashcard word="딱">(Adverb) Exactly, just right</flashcard>\n'
            '</vocab>\n'
            '<grammar>\n'
            '<grammar_pattern title="-네요 Ending">Expresses mild surprise or realization. More gentle/observational than -아요/어요.</grammar_pattern>\n'
            '</grammar>\n\n'
            'Topic: {topic}\n'
            'User Native Language: {native_language}\n'
            'Target Language: {study_language}\n'
            'Begin the conversation or continue it naturally.'
        ),
    }
}
