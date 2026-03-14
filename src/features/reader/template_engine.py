"""
Template Engine for Adventure Graded Reader.

This module provides template-based story generation using pre-written
templates with placeholder substitution. This mode requires no API calls
during gameplay and works offline.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import json
import random
import re
from datetime import datetime

from src.core.database import FlashcardDatabase
from .models import StoryPassage, NewWord, Choice, StoryContext, VocabularyConstraints
from .exceptions import TemplateNotFoundError


@dataclass
class StoryTemplate:
    """
    Represents a story template node.
    
    Attributes:
        id: Database ID
        genre: Story genre (mystery, adventure, fantasy)
        node_id: Unique identifier for this template node
        template_text: Text with placeholders like {LOCATION}, {ACTION}
        suggested_vocab: List of suggested new words to introduce
        choices: List of choice templates
        metadata: Additional template data
    """
    id: Optional[int]
    genre: str
    node_id: str
    template_text: str
    suggested_vocab: List[Dict[str, str]]  # [{"word": "...", "translation": "..."}]
    choices: List[Dict[str, str]]  # [{"id": 1, "text": "...", "next_node": "..."}]
    metadata: Dict[str, any]


class TemplateEngine:
    """
    Engine for generating stories from templates.
    
    This engine loads pre-written story templates, fills placeholders with
    words from the user's known vocabulary, and navigates branching story
    paths based on user choices.
    """
    
    def __init__(self, db: FlashcardDatabase):
        """
        Initialize TemplateEngine.
        
        Args:
            db: FlashcardDatabase instance for loading templates
        """
        self.db = db
        self._template_cache: Dict[str, List[StoryTemplate]] = {}
    
    def load_templates(self, genre: str) -> List[StoryTemplate]:
        """
        Load all templates for a genre from database.
        
        Args:
            genre: Story genre (mystery, adventure, fantasy)
        
        Returns:
            List of StoryTemplate objects
        
        Raises:
            TemplateNotFoundError: If no templates found for genre
        
        Preconditions:
            - genre is non-empty string
            - Database connection is active
        
        Postconditions:
            - Returns list of templates (non-empty)
            - Templates are cached for performance
        """
        if not genre or not genre.strip():
            raise ValueError("genre must be non-empty")
        
        # Check cache first
        if genre in self._template_cache:
            cached = self._template_cache[genre]
            if not cached:
                raise TemplateNotFoundError(f"No templates found for genre: {genre}")
            return cached
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, genre, node_id, template_text, suggested_vocab, choices, metadata
            FROM story_templates
            WHERE genre = ?
            ORDER BY node_id
        """, (genre,))
        
        templates = []
        for row in cursor.fetchall():
            template = StoryTemplate(
                id=row[0],
                genre=row[1],
                node_id=row[2],
                template_text=row[3],
                suggested_vocab=json.loads(row[4]) if row[4] else [],
                choices=json.loads(row[5]) if row[5] else [],
                metadata=json.loads(row[6]) if row[6] else {}
            )
            templates.append(template)
        
        # Raise error if no templates found
        if not templates:
            raise TemplateNotFoundError(
                f"No templates found for genre '{genre}'. "
                f"Please seed the database with templates or choose a different genre."
            )
        
        # Cache the templates
        self._template_cache[genre] = templates
        
        return templates
    
    def get_template_by_node_id(self, genre: str, node_id: str) -> Optional[StoryTemplate]:
        """
        Get a specific template by its node_id.
        
        Args:
            genre: Story genre
            node_id: Unique node identifier
        
        Returns:
            StoryTemplate if found, None otherwise
        """
        templates = self.load_templates(genre)
        for template in templates:
            if template.node_id == node_id:
                return template
        return None
    
    def get_next_node(self, genre: str, current_node: str, choice_id: int) -> Optional[str]:
        """
        Get the next node ID based on current node and choice.
        
        Args:
            genre: Story genre
            current_node: Current node ID
            choice_id: ID of choice made by user
        
        Returns:
            Next node ID, or None if not found
        
        Preconditions:
            - current_node exists in templates
            - choice_id is valid for current node
        
        Postconditions:
            - Returns valid node_id or None
        """
        template = self.get_template_by_node_id(genre, current_node)
        if not template:
            return None
        
        # Find the choice with matching ID
        for choice in template.choices:
            if choice.get("id") == choice_id:
                return choice.get("next_node")
        
        return None
    
    def extract_placeholders(self, text: str) -> List[Dict[str, str]]:
        """
        Extract placeholders from template text.
        
        Placeholders are in format {CATEGORY} or {CATEGORY:default_value}
        
        Args:
            text: Template text
        
        Returns:
            List of placeholder dicts with 'tag', 'category', 'default_value'
        
        Example:
            "{LOCATION} has a {OBJECT:door}" ->
            [
                {"tag": "{LOCATION}", "category": "LOCATION", "default_value": ""},
                {"tag": "{OBJECT:door}", "category": "OBJECT", "default_value": "door"}
            ]
        """
        placeholders = []
        pattern = r'\{([A-Z_]+)(?::([^}]+))?\}'
        
        for match in re.finditer(pattern, text):
            tag = match.group(0)
            category = match.group(1)
            default_value = match.group(2) or ""
            
            placeholders.append({
                "tag": tag,
                "category": category,
                "default_value": default_value
            })
        
        return placeholders
    
    def filter_words_by_category(self, known_words: Set[str], category: str) -> List[str]:
        """
        Filter known words by category.
        
        This is a simple implementation that returns random words.
        In a production system, words would be tagged by category in the database.
        
        Args:
            known_words: Set of known words
            category: Category name (LOCATION, ACTION, OBJECT, etc.)
        
        Returns:
            List of words matching category
        """
        # For now, return random words from known vocabulary
        # TODO: Implement proper word categorization in database
        words = list(known_words)
        if not words:
            return []
        
        # Return a subset of words (simulating category filtering)
        sample_size = min(5, len(words))
        return random.sample(words, sample_size)
    
    def fill_template(self, template: StoryTemplate, vocabulary: VocabularyConstraints) -> StoryPassage:
        """
        Fill a template with words from known vocabulary.
        
        Args:
            template: StoryTemplate to fill
            vocabulary: VocabularyConstraints with known words
        
        Returns:
            StoryPassage with filled text and choices
        
        Preconditions:
            - template is valid StoryTemplate
            - vocabulary.known_words is non-empty
        
        Postconditions:
            - Returns valid StoryPassage
            - All placeholders are replaced
            - Passage contains 1-2 new words
            - Passage contains 2-3 choices
        """
        filled_text = template.template_text
        
        # Extract and fill placeholders
        placeholders = self.extract_placeholders(filled_text)
        
        for placeholder in placeholders:
            category = placeholder["category"]
            default_value = placeholder["default_value"]
            tag = placeholder["tag"]
            
            # Get candidate words for this category
            candidates = self.filter_words_by_category(vocabulary.known_words, category)
            
            if candidates:
                word = random.choice(candidates)
            elif default_value:
                word = default_value
            else:
                word = f"[{category}]"  # Fallback
            
            filled_text = filled_text.replace(tag, word)
        
        # Select 1-2 new words to introduce
        new_words = self._select_new_words(
            template.suggested_vocab,
            vocabulary,
            min_count=1,
            max_count=vocabulary.max_new_words
        )
        
        # Incorporate new words into text
        for new_word in new_words:
            filled_text = self._incorporate_new_word(filled_text, new_word.word)
        
        # Build choices from template
        choices = []
        for i, choice_template in enumerate(template.choices[:3]):  # Max 3 choices
            choice_text = choice_template.get("text", "")
            
            # Fill placeholders in choice text
            choice_placeholders = self.extract_placeholders(choice_text)
            for placeholder in choice_placeholders:
                candidates = self.filter_words_by_category(vocabulary.known_words, placeholder["category"])
                word = random.choice(candidates) if candidates else placeholder["default_value"]
                choice_text = choice_text.replace(placeholder["tag"], word)
            
            choice = Choice(
                id=choice_template.get("id", i + 1),
                text=choice_text,
                description=choice_template.get("description", "")
            )
            choices.append(choice)
        
        # Ensure we have at least 2 choices
        if len(choices) < 2:
            choices.append(Choice(id=99, text="Continue", description="Continue the story"))
        if len(choices) < 2:
            choices.append(Choice(id=100, text="Go back", description="Go back to the previous location"))
        
        # Create passage
        passage = StoryPassage(
            session_id=0,  # Will be set by caller
            passage_number=0,  # Will be set by caller
            story_text=filled_text,
            new_words=new_words,
            choices=choices,
            created_at=datetime.now().isoformat()
        )
        
        return passage
    
    def _select_new_words(
        self,
        suggested_vocab: List[Dict[str, str]],
        vocabulary: VocabularyConstraints,
        min_count: int = 1,
        max_count: int = 2
    ) -> List[NewWord]:
        """
        Select new words to introduce from suggested vocabulary.
        
        Args:
            suggested_vocab: List of suggested word dicts
            vocabulary: VocabularyConstraints
            min_count: Minimum number of new words
            max_count: Maximum number of new words
        
        Returns:
            List of NewWord objects
        """
        # Filter out words already known or in session
        all_known = vocabulary.known_words | vocabulary.session_words
        
        available_words = [
            w for w in suggested_vocab
            if w.get("word", "").lower() not in {word.lower() for word in all_known}
        ]
        
        if not available_words:
            # Fallback: create generic new words
            return [
                NewWord(
                    word="새로운",
                    translation="new",
                    context_sentence="This is a 새로운 word."
                )
            ]
        
        # Select random words
        count = min(max_count, len(available_words))
        count = max(min_count, count)
        
        selected = random.sample(available_words, count)
        
        new_words = []
        for word_data in selected:
            new_word = NewWord(
                word=word_data.get("word", ""),
                translation=word_data.get("translation", ""),
                context_sentence=word_data.get("context", f"Context with {word_data.get('word', '')}")
            )
            new_words.append(new_word)
        
        return new_words
    
    def _incorporate_new_word(self, text: str, word: str) -> str:
        """
        Incorporate a new word into the text if not already present.
        
        Args:
            text: Story text
            word: New word to incorporate
        
        Returns:
            Text with word incorporated
        """
        if word in text:
            return text
        
        # Simple incorporation: add at the end
        # TODO: Implement smarter insertion based on template insertion points
        return f"{text} {word}."
    
    def get_available_genres(self) -> List[str]:
        """
        Get list of available story genres.
        
        Returns:
            List of genre names
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT DISTINCT genre FROM story_templates ORDER BY genre")
        return [row[0] for row in cursor.fetchall()]
    
    def save_template(self, template: StoryTemplate) -> int:
        """
        Save a template to the database.
        
        Args:
            template: StoryTemplate to save
        
        Returns:
            Template ID
        """
        cursor = self.db.conn.cursor()
        
        if template.id:
            # Update existing
            cursor.execute("""
                UPDATE story_templates
                SET template_text = ?,
                    suggested_vocab = ?,
                    choices = ?,
                    metadata = ?
                WHERE id = ?
            """, (
                template.template_text,
                json.dumps(template.suggested_vocab),
                json.dumps(template.choices),
                json.dumps(template.metadata),
                template.id
            ))
            self.db.conn.commit()
            return template.id
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO story_templates (genre, node_id, template_text, suggested_vocab, choices, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                template.genre,
                template.node_id,
                template.template_text,
                json.dumps(template.suggested_vocab),
                json.dumps(template.choices),
                json.dumps(template.metadata)
            ))
            self.db.conn.commit()
            
            # Clear cache for this genre
            if template.genre in self._template_cache:
                del self._template_cache[template.genre]
            
            return cursor.lastrowid
    
    def _extract_word_from_question(self, question: str) -> str:
        """
        Extract the word from a question format string.
        
        Handles various formats:
        - Plain word: "학교"
        - With context: "학교 (in sentence: ...)"
        - With translation: "학교 - school"
        - With brackets: "학교 [noun]"
        
        Args:
            question: Question string in various formats
        
        Returns:
            The extracted word
        """
        # Remove common suffixes
        word = question.strip()
        
        # Remove translation (after dash)
        if " - " in word:
            word = word.split(" - ")[0].strip()
        
        # Remove context (in parentheses)
        if " (" in word:
            word = word.split(" (")[0].strip()
        
        # Remove brackets
        if " [" in word:
            word = word.split(" [")[0].strip()
        
        return word
