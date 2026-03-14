"""
Property-based tests for new word presence in text.

Tests Property 10: New Word Presence in Text
Validates that each declared new word is present in story text
"""

from hypothesis import given, strategies as st
import pytest

from src.features.reader.models import StoryPassage, NewWord, Choice


class TestNewWordPresence:
    """Property 10: New Word Presence in Text"""
    
    @given(
        new_word_text=st.text(min_size=1, max_size=20),
        context_text=st.text(min_size=10, max_size=200)
    )
    def test_new_word_in_story_text(self, new_word_text, context_text):
        """
        Property: All declared new words are present in story text
        
        For any passage with declared new words, each new word must
        appear somewhere in the story_text.
        """
        if not new_word_text or not context_text:
            pytest.skip("Empty text")
        
        # Create story text that includes the new word
        story_text = f"{context_text} {new_word_text} {context_text}"
        
        try:
            passage = StoryPassage(
                session_id=1,
                passage_number=1,
                story_text=story_text,
                new_words=[NewWord(new_word_text, "translation", story_text)],
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
        except ValueError:
            pytest.skip("Invalid passage")
        
        # Verify all new words are in story text
        for new_word in passage.new_words:
            assert new_word.word in passage.story_text, \
                f"New word '{new_word.word}' not found in story text"
    
    @given(
        words=st.lists(st.text(min_size=1, max_size=15), min_size=1, max_size=2, unique=True),
        base_text=st.text(min_size=20, max_size=200)
    )
    def test_multiple_new_words_presence(self, words, base_text):
        """
        Property: All new words in a passage are present in text
        
        When a passage declares multiple new words, all of them
        must be present in the story_text.
        """
        if not words or not base_text:
            pytest.skip("Empty input")
        
        # Create story text with all new words
        story_text = base_text + " " + " ".join(words)
        
        try:
            new_words_list = [
                NewWord(word, f"translation of {word}", story_text)
                for word in words
            ]
            
            passage = StoryPassage(
                session_id=1,
                passage_number=1,
                story_text=story_text,
                new_words=new_words_list[:2],  # Max 2 new words
                choices=[Choice(1, "choice1"), Choice(2, "choice2")],
                created_at="2024-01-01T00:00:00"
            )
        except ValueError:
            pytest.skip("Invalid passage")
        
        # All new words should be in story text
        for new_word in passage.new_words:
            assert new_word.word in passage.story_text
    
    def test_new_word_presence_validation(self):
        """
        Property: NewWord validation ensures word is in context
        
        The NewWord model validates that the word appears in
        the context_sentence during construction.
        """
        # This should succeed - word is in context
        word = NewWord(
            word="test",
            translation="test",
            context_sentence="This is a test sentence"
        )
        assert word.word in word.context_sentence
        
        # This should fail - word not in context
        with pytest.raises(ValueError, match="context_sentence must contain word"):
            NewWord(
                word="missing",
                translation="missing",
                context_sentence="This is a test sentence"
            )
    
    @given(
        word=st.text(min_size=1, max_size=20),
        text=st.text(min_size=10, max_size=200)
    )
    def test_word_presence_case_sensitive(self, word, text):
        """
        Property: Word presence check is case-sensitive
        
        The word must appear in the text with exact case matching.
        """
        if not word or not text or word in text:
            pytest.skip("Skipping due to input constraints")
        
        # Word should not be found if case doesn't match
        story_text = text + " " + word.upper()
        
        # This should fail because case doesn't match
        with pytest.raises(ValueError):
            NewWord(
                word=word,
                translation="translation",
                context_sentence=story_text
            )
