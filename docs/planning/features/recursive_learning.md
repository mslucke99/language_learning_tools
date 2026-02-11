# Feature Specification: Recursive Learning ("The Rabbit Hole")

## Overview
Recursive Learning allows users to explore knowledge depth-first. When an LLM explanation or dictionary definition contains a word the user doesn't know, they can "click through" to create a new learning item (flashcard) for *that* word, creating a dependency chain.

## Goals
1.  **Close Knowledge Gaps**: Prevent "illusion of competence" where a user memorizes a definition they don't actually understand.
2.  **Visualize Dependencies**: Show users that "To understand concept A, you first need B and C."
3.  **Natural Exploration**: Mimic how curiosity works in natural learning.

## Workflow
1.  **Trigger**: User is viewing a Flashcard or Chat Response.
2.  **Interaction**: User clicks on a difficult word in the *explanation/definition*.
3.  **Action**:
    *   System looks up the new word in the `LocalDictionary`.
    *   System proposes a new Flashcard for this child word.
    *   System records a `dependency` link: `Parent_Card_ID -> Child_Card_ID`.
4.  **Review Logic**:
    *   The system can (optionally) suspend the Parent Card until the Child Card is mastered ("Blocked by Dependency").

## Technical Requirements
*   **UI Hyperlinking**: All text views (Chat, Flashcard Back) must support clickable tokens (already partially planned with `TokenizerService`).
*   **Data Model**: New `card_dependencies` table in SQLite (`parent_id`, `child_id`).
*   **Graph Visualization**: (Optional) A node graph showing how concepts link together.

## UI Components
*   **"Inspect Mode"**: A toggle in the Chat/Flashcard view that turns all words into clickable tokens.
*   **Dependency Badge**: Visual indicator on a card showing "Blocked by X unlearned cards".
