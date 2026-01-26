# AI Prompt Review & Suggestions

This document contains a review of the current AI prompts in `src/services/prompts.py` and suggestions for further refinement.

## Current Strengths
- **Placeholders**: Effective use of `{word}`, `{sentence}`, `{study_language}`, etc.
- **Structured Output**: Consistent XML-like tags (`<flashcard>`, `<grammar_pattern>`) for automated extraction.
- **Few-Shot Examples**: Good coverage of "Related Items" generation in word and sentence prompts.

## Areas for Improvement

### 1. Missing Examples for Word Definitions
The **Definition** and **Explanation** prompts (lines 8–32) lack few-shot examples.
*   **Recommendation**: Add examples for both "Professional Tutor" (native) and "Simple Beginner" (study) styles. This ensures consistent length and helpful "Memory Hooks."

### 2. Pronunciation Style Ambiguity
The **Pronunciation** prompt (line 123) is vague about the representation style.
*   **Recommendation**: Specify the desired format: IPA, standard romanization, or approximated phonetics. Adding an example (e.g., Korean sound-change rules) would clarify expectations for complex languages.

### 3. Writing Lab Feedback Constraints
The **Grade & Feedback** prompt (line 162) might lead to "over-correction."
*   **Recommendation**: Add a constraint to focus on 3-4 high-impact errors rather than correcting every minor detail. Instructions like *"Provide a rewritten version only if necessary for clarity"* can prevent overwhelming the learner.

### 4. Logic for "Basic" Cases (Negative Constraints)
While some "no suggestions" examples exist, more explicit constraints are needed.
*   **Recommendation**: Instruction: *"Only suggest a grammar pattern if it is level-appropriate. Do not suggest patterns for absolute foundations (like SVO order) unless explicitly asked or particularly complex in the target language."*

### 5. Topic Generation Scenarios
The **Generate Topic** prompt (line 154) asks for a "scenario" but doesn't define how rich it should be.
*   **Recommendation**: Add a few-shot example showing a situational prompt (e.g., *"Dealing with a lost item at a train station"*) rather than a generic topic (e.g., *"My favorite food"*).

## Next Steps
- [ ] Draft example texts for Word Definitions.
- [ ] Define phonetic standards for Pronunciation.
- [ ] Update Writing Lab prompts with "Level-Appropriate" constraints.
