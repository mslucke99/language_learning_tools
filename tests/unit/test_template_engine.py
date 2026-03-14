"""
Unit tests for TemplateEngine.

Tests template loading, placeholder extraction, filling, and navigation.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock

from src.features.reader.template_engine import TemplateEngine, StoryTemplate
from src.features.reader.models import VocabularyConstraints
from src.features.reader.exceptions import TemplateNotFoundError


class TestTemplateEngine:
    """Test cases for TemplateEngine"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database for testing"""
        db = Mock()
        db.conn = Mock()
        return db
    
    @pytest.fixture
    def engine(self, mock_db):
        """Create a TemplateEngine instance with mock database"""
        return TemplateEngine(mock_db)
    
    @pytest.fixture
    def sample_template(self):
        """Create a sample story template"""
        return StoryTemplate(
            id=1,
            genre="mystery",
            node_id="start",
            template_text="You enter a {LOCATION}. A {OBJECT} is on the table.",
            suggested_vocab=[
                {"word": "mysterious", "translation": "mysterious", "context": "mysterious place"},
                {"word": "ancient", "translation": "ancient", "context": "ancient artifact"}
            ],
            choices=[
                {"id": 1, "text": "Examine the {OBJECT}", "next_node": "examine"},
                {"id": 2, "text": "Leave the {LOCATION}", "next_node": "leave"}
            ],
            metadata={"difficulty": "easy"}
        )
    
    def test_load_templates_success(self, engine, mock_db, sample_template):
        """Test loading templates from database"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        templates = engine.load_templates("mystery")
        
        assert len(templates) == 1
        assert templates[0].genre == "mystery"
        assert templates[0].node_id == "start"
    
    def test_load_templates_not_found(self, engine, mock_db):
        """Test loading templates when none exist"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_db.conn.cursor.return_value = mock_cursor
        
        with pytest.raises(TemplateNotFoundError):
            engine.load_templates("nonexistent")
    
    def test_load_templates_caching(self, engine, mock_db, sample_template):
        """Test that templates are cached after loading"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        # First load
        templates1 = engine.load_templates("mystery")
        
        # Second load should use cache
        templates2 = engine.load_templates("mystery")
        
        assert templates1 == templates2
        # Database should only be queried once
        assert mock_cursor.execute.call_count == 1
    
    def test_get_template_by_node_id(self, engine, mock_db, sample_template):
        """Test retrieving a specific template by node ID"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        template = engine.get_template_by_node_id("mystery", "start")
        
        assert template is not None
        assert template.node_id == "start"
    
    def test_get_template_by_node_id_not_found(self, engine, mock_db, sample_template):
        """Test retrieving non-existent template"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        template = engine.get_template_by_node_id("mystery", "nonexistent")
        
        assert template is None
    
    def test_get_next_node(self, engine, mock_db, sample_template):
        """Test getting next node based on choice"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        next_node = engine.get_next_node("mystery", "start", 1)
        
        assert next_node == "examine"
    
    def test_get_next_node_invalid_choice(self, engine, mock_db, sample_template):
        """Test getting next node with invalid choice ID"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "mystery", "start", "You enter a {LOCATION}.",
             json.dumps(sample_template.suggested_vocab),
             json.dumps(sample_template.choices),
             json.dumps(sample_template.metadata))
        ]
        mock_db.conn.cursor.return_value = mock_cursor
        
        next_node = engine.get_next_node("mystery", "start", 999)
        
        assert next_node is None
    
    def test_extract_placeholders_simple(self, engine):
        """Test extracting placeholders from template text"""
        text = "You enter a {LOCATION}. A {OBJECT} is here."
        
        placeholders = engine.extract_placeholders(text)
        
        assert len(placeholders) == 2
        assert placeholders[0]["category"] == "LOCATION"
        assert placeholders[1]["category"] == "OBJECT"
    
    def test_extract_placeholders_with_defaults(self, engine):
        """Test extracting placeholders with default values"""
        text = "You see a {OBJECT:door} and a {LOCATION:room}."
        
        placeholders = engine.extract_placeholders(text)
        
        assert len(placeholders) == 2
        assert placeholders[0]["default_value"] == "door"
        assert placeholders[1]["default_value"] == "room"
    
    def test_extract_placeholders_none(self, engine):
        """Test extracting placeholders when none exist"""
        text = "You enter a room. Nothing special here."
        
        placeholders = engine.extract_placeholders(text)
        
        assert len(placeholders) == 0
    
    def test_filter_words_by_category(self, engine):
        """Test filtering words by category"""
        known_words = {"room", "house", "building", "door", "window"}
        
        words = engine.filter_words_by_category(known_words, "LOCATION")
        
        assert len(words) > 0
        assert all(word in known_words for word in words)
    
    def test_filter_words_by_category_empty(self, engine):
        """Test filtering with empty vocabulary"""
        known_words = set()
        
        words = engine.filter_words_by_category(known_words, "LOCATION")
        
        assert len(words) == 0
    
    def test_fill_template_basic(self, engine, sample_template):
        """Test filling a template with vocabulary"""
        vocabulary = VocabularyConstraints(
            known_words={"room", "table", "key", "examine", "leave"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        passage = engine.fill_template(sample_template, vocabulary)
        
        assert passage is not None
        assert passage.story_text is not None
        assert len(passage.new_words) >= 1
        assert len(passage.new_words) <= 2
        assert len(passage.choices) >= 2
        assert len(passage.choices) <= 3
    
    def test_fill_template_placeholder_replacement(self, engine):
        """Test that placeholders are replaced in filled template"""
        template = StoryTemplate(
            id=1,
            genre="test",
            node_id="test",
            template_text="You see a {OBJECT}.",
            suggested_vocab=[],
            choices=[],
            metadata={}
        )
        
        vocabulary = VocabularyConstraints(
            known_words={"key", "door", "box"},
            session_words=set(),
            max_new_words=1,
            min_coverage=0.95
        )
        
        passage = engine.fill_template(template, vocabulary)
        
        # Check that placeholders were replaced
        assert "{OBJECT}" not in passage.story_text
    
    def test_fill_template_new_words_in_text(self, engine, sample_template):
        """Test that new words are incorporated into the text"""
        vocabulary = VocabularyConstraints(
            known_words={"room", "table", "key"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        passage = engine.fill_template(sample_template, vocabulary)
        
        # All new words should be in the story text
        for new_word in passage.new_words:
            assert new_word.word in passage.story_text
    
    def test_fill_template_choices_generated(self, engine, sample_template):
        """Test that choices are generated from template"""
        vocabulary = VocabularyConstraints(
            known_words={"room", "table", "key", "examine", "leave"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        passage = engine.fill_template(sample_template, vocabulary)
        
        assert len(passage.choices) >= 2
        assert all(choice.text for choice in passage.choices)
    
    def test_fill_template_minimum_choices(self, engine):
        """Test that minimum 2 choices are generated"""
        template = StoryTemplate(
            id=1,
            genre="test",
            node_id="test",
            template_text="A story.",
            suggested_vocab=[{"word": "new", "translation": "new"}],
            choices=[],  # No choices in template
            metadata={}
        )
        
        vocabulary = VocabularyConstraints(
            known_words={"word"},
            session_words=set(),
            max_new_words=2,
            min_coverage=0.95
        )
        
        passage = engine.fill_template(template, vocabulary)
        
        # Should have at least 2 choices (fallback)
        assert len(passage.choices) >= 2
    
    def test_get_available_genres(self, engine, mock_db):
        """Test getting list of available genres"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("mystery",), ("adventure",), ("fantasy",)]
        mock_db.conn.cursor.return_value = mock_cursor
        
        genres = engine.get_available_genres()
        
        assert len(genres) == 3
        assert "mystery" in genres
        assert "adventure" in genres
        assert "fantasy" in genres
    
    def test_save_template_new(self, engine, mock_db, sample_template):
        """Test saving a new template"""
        sample_template.id = None  # Mark as new
        mock_cursor = Mock()
        mock_cursor.lastrowid = 42
        mock_db.conn.cursor.return_value = mock_cursor
        
        template_id = engine.save_template(sample_template)
        
        assert template_id == 42
        mock_cursor.execute.assert_called()
    
    def test_save_template_update(self, engine, mock_db, sample_template):
        """Test updating an existing template"""
        sample_template.id = 1  # Mark as existing
        mock_cursor = Mock()
        mock_db.conn.cursor.return_value = mock_cursor
        
        template_id = engine.save_template(sample_template)
        
        assert template_id == 1
        mock_cursor.execute.assert_called()
    
    def test_extract_word_from_question_formats(self, engine):
        """Test extracting words from various question formats"""
        # Plain word
        assert engine._extract_word_from_question("학교") == "학교"
        
        # With context
        assert engine._extract_word_from_question("학교 (in sentence: ...)") == "학교"
        
        # With translation
        assert engine._extract_word_from_question("학교 - school") == "학교"
        
        # With brackets
        assert engine._extract_word_from_question("학교 [noun]") == "학교"
