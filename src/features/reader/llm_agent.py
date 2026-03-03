"""
LLM Agent for Adventure Graded Reader.

This module provides LLM-based story generation with vocabulary constraints.
The agent dynamically generates story content while adhering to the user's
known vocabulary and introducing exactly 1-2 new words per passage.
"""

from typing import Optional, Dict
import json
import time

from src.services.llm_service import LLMService, get_ai_client
from .models import StoryPassage, StoryContext, VocabularyConstraints, NewWord, Choice, GenerationMode
from .validator import VocabularyValidator
from .exceptions import LLMGenerationError
from datetime import datetime


class AdventureReaderAgent:
    """
    Agent for generating story passages using LLM.
    
    This agent builds prompts with vocabulary constraints, calls the LLM service,
    parses JSON responses, and validates output against vocabulary requirements.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize AdventureReaderAgent.
        
        Args:
            llm_service: Optional LLMService instance. If None, uses default.
        """
        self.llm_service = llm_service or get_ai_client()
        self.validator = VocabularyValidator()
    
    def generate_story_passage(
        self,
        context: StoryContext,
        constraints: VocabularyConstraints,
        session_id: int = 0,
        passage_number: int = 0,
        max_retries: int = 3
    ) -> StoryPassage:
        """
        Generate a story passage using LLM with retry logic.
        
        Args:
            context: Current story context
            constraints: Vocabulary constraints
            session_id: ID of story session
            passage_number: Sequential passage number
            max_retries: Maximum number of retry attempts
        
        Returns:
            StoryPassage object
        
        Raises:
            LLMGenerationError: If generation fails after all retries
        
        Preconditions:
            - LLM service is initialized and available
            - context contains valid story state
            - constraints.known_words is non-empty
        
        Postconditions:
            - Returns valid passage meeting vocabulary constraints
            - If LLM fails after retries, raises LLMGenerationError
            - No exceptions propagate to caller except LLMGenerationError
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # Build prompt with vocabulary constraints
                prompt = self.build_prompt(context, constraints)
                
                # Call LLM with timeout
                llm_response = self.llm_service.generate_response(prompt, timeout=60)
                
                if not llm_response:
                    retry_count += 1
                    last_error = "LLM returned empty response"
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                
                # Parse JSON response
                passage = self.parse_response(
                    llm_response,
                    session_id=session_id,
                    passage_number=passage_number
                )
                
                # Validate output
                validation = self.validator.validate_vocabulary(passage, constraints)
                
                if validation.is_valid:
                    return passage
                else:
                    # Retry with stricter prompt
                    retry_count += 1
                    last_error = f"Validation failed: {validation.message}"
                    # On next retry, the prompt will be rebuilt with updated context
                    time.sleep(1)
            
            except json.JSONDecodeError as e:
                retry_count += 1
                last_error = f"JSON parsing error: {str(e)}"
                time.sleep(2 ** retry_count)
            
            except Exception as e:
                retry_count += 1
                last_error = f"Generation error: {str(e)}"
                time.sleep(2 ** retry_count)
        
        # All retries failed
        raise LLMGenerationError(
            f"Failed to generate passage after {max_retries} attempts. Last error: {last_error}"
        )
    
    def build_prompt(
        self,
        context: StoryContext,
        constraints: VocabularyConstraints
    ) -> str:
        """
        Build LLM prompt with vocabulary constraints.
        
        Args:
            context: Story context
            constraints: Vocabulary constraints
        
        Returns:
            Formatted prompt string
        
        Preconditions:
            - context is valid StoryContext
            - constraints.known_words is non-empty
        
        Postconditions:
            - Returns non-empty prompt string
            - Prompt includes known words list as JSON
            - Prompt includes vocabulary constraints
        """
        # Convert known words to list for JSON serialization
        known_words_list = sorted(list(constraints.known_words))[:100]  # Limit to 100 for prompt size
        known_words_json = json.dumps(known_words_list, ensure_ascii=False)
        
        # Build context summary
        context_summary = f"""
Genre: {context.genre}
Location: {context.current_location}
Characters: {', '.join(context.characters) if context.characters else 'None yet'}
Plot so far: {context.plot_summary}
Mood: {context.mood}
"""
        
        # Build the prompt using the template
        prompt = f"""You are an interactive fiction engine for a language learner.

**CRITICAL CONSTRAINTS:**
1. You MUST use ONLY words from the known vocabulary list below (95% of your output).
2. You may introduce EXACTLY TWO new vocabulary words per response.
3. Keep sentences grammatically simple and clear.
4. End with exactly TWO clear choices for the user.

**Known Vocabulary (use these words):**
{known_words_json}

**Current Story Context:**
{context_summary}

**Your Task:**
Continue the story based on the context above. Generate the next passage of the story.

**Output Format (JSON):**
{{
  "story_text": "The narrative text in the target language...",
  "new_words": [
    {{"word": "word1", "translation": "translation1", "context_sentence": "sentence containing word1"}},
    {{"word": "word2", "translation": "translation2", "context_sentence": "sentence containing word2"}}
  ],
  "choices": [
    {{"id": 1, "text": "Choice 1 in target language", "description": "Brief description"}},
    {{"id": 2, "text": "Choice 2 in target language", "description": "Brief description"}}
  ]
}}

**Important:**
- story_text should be 2-4 sentences
- Use ONLY known vocabulary + the 2 new words
- Make choices meaningful and advance the plot
- Ensure new words appear in story_text
- Keep it engaging and appropriate for language learners

Generate the JSON response now:"""
        
        return prompt
    
    def parse_response(
        self,
        llm_output: str,
        session_id: int = 0,
        passage_number: int = 0
    ) -> StoryPassage:
        """
        Parse LLM JSON response into StoryPassage.
        
        Args:
            llm_output: Raw LLM response string
            session_id: Session ID for passage
            passage_number: Passage number
        
        Returns:
            StoryPassage object
        
        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If required fields are missing
        
        Preconditions:
            - llm_output is non-empty string
        
        Postconditions:
            - Returns valid StoryPassage object
            - All required fields are populated
        """
        # Try to extract JSON from response (LLM might add extra text)
        llm_output = llm_output.strip()
        
        # Find JSON block
        start_idx = llm_output.find('{')
        end_idx = llm_output.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise json.JSONDecodeError("No JSON found in response", llm_output, 0)
        
        json_str = llm_output[start_idx:end_idx + 1]
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Extract fields
        story_text = data.get("story_text", "")
        if not story_text:
            raise ValueError("story_text is required")
        
        # Parse new words
        new_words_data = data.get("new_words", [])
        if not isinstance(new_words_data, list):
            raise ValueError("new_words must be a list")
        
        new_words = []
        for word_data in new_words_data:
            new_word = NewWord(
                word=word_data.get("word", ""),
                translation=word_data.get("translation", ""),
                context_sentence=word_data.get("context_sentence", story_text)
            )
            new_words.append(new_word)
        
        # Ensure we have 1-2 new words
        if not new_words:
            # Create a placeholder if LLM didn't provide any
            new_words = [NewWord(
                word="[new]",
                translation="new word",
                context_sentence=story_text
            )]
        
        # Parse choices
        choices_data = data.get("choices", [])
        if not isinstance(choices_data, list):
            raise ValueError("choices must be a list")
        
        choices = []
        for i, choice_data in enumerate(choices_data):
            choice = Choice(
                id=choice_data.get("id", i + 1),
                text=choice_data.get("text", ""),
                description=choice_data.get("description", "")
            )
            choices.append(choice)
        
        # Ensure we have 2-3 choices
        if len(choices) < 2:
            choices.append(Choice(id=99, text="Continue", description="Continue the story"))
        
        # Create passage
        passage = StoryPassage(
            session_id=session_id,
            passage_number=passage_number,
            story_text=story_text,
            new_words=new_words[:2],  # Limit to 2
            choices=choices[:3],  # Limit to 3
            created_at=datetime.now().isoformat()
        )
        
        return passage
    
    def is_available(self) -> bool:
        """
        Check if LLM service is available.
        
        Returns:
            True if LLM service is available, False otherwise
        """
        return self.llm_service.is_available()
