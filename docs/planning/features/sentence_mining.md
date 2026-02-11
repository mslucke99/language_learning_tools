# Feature Specification: Context-Aware Sentence Mining

## Overview
This feature allows users to import raw texts (books, subtitles, articles) and automatically find sentences that are optimal for learning. Based on Stephen Krashen's "Input Hypothesis," it targets "i+1" sentences—those where the user knows every word except one.

## Goals
1.  **Reduce Friction**: Eliminate manual hunting for good example sentences.
2.  **Ensure Comprehension**: Guarantee that flashcards are not too difficult (i+10) or too easy (i+0).
3.  **Leverage Local Data**: Use the local dictionary and user's known vocabulary history (from Anki/Flashcards DB) to determine "known" status.

## Workflow
1.  **Import**: User uploads a text file (.txt, .srt, .epub).
2.  **Analysis**:
    *   The `TokenizerService` splits text into sentences and tokens.
    *   The system checks each unique token against the `UserVocabulary` database (to be created).
3.  **Classification**:
    *   **Level 0 (i+0)**: All words known. Good for review or speed reading.
    *   **Level 1 (i+1)**: Update 1 unknown word. **High Priority for Flashcards.**
    *   **Level 2+**: Too many unknown words.
4.  **Generation**:
    *   User selects an "i+1" sentence.
    *   System generates a flashcard:
        *   **Front**: The sentence (with the unknown word highlighted).
        *   **Back**: Definition of the unknown word + Audio (from Dictionary) + Translation (from LLM).

## Technical Requirements
*   **Tokenizer**: Must handle sentence splitting robustly (already implemented for supported languages).
*   **Vocabulary Tracker**: A new SQLite table `known_words` to track lemmas the user has marked as "Known".
*   **Performance**: processing a whole book requires efficient batch lookups.

## UI Components
*   **Mining Dashboard**: A view showing the imported text with color-coded sentences (Green=i+0, Yellow=i+1, Red=i+2+).
*   **One-Click Add**: A button next to Yellow sentences to "Create Card".
