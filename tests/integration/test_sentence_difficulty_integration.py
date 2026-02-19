"""
Integration tests for sentence difficulty: full pipeline with DB and optional scorer.
"""
import os
import tempfile
import pytest

from src.core.database import FlashcardDatabase
from src.services.text.tokenizer_service import TokenizerService
from src.services.text.sentence_miner import SentenceMiner, MiningResult
from src.services.text.sentence_difficulty import (
    SentenceDifficultyScorer,
    UserProfile,
    make_tokenizer_adapter_from_tokenizer_service,
    make_recall_provider_from_db,
)
from src.services.text.difficulty_resources import FrequencyList, ResourceBundle


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = FlashcardDatabase(path)
    yield database
    try:
        database.close()
    except Exception:
        pass
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def tokenizer():
    return TokenizerService()


@pytest.fixture
def freq_list():
    """Minimal frequency list for English."""
    word_to_rank = {
        "the": 1, "cat": 2, "sat": 3, "on": 4, "mat": 5,
        "hello": 10, "world": 20, "photosynthesis": 5000,
    }
    return FrequencyList(word_to_rank, 10000)


def test_miner_without_scorer(temp_db, tokenizer):
    """Mining works without difficulty scorer; no difficulty fields."""
    miner = SentenceMiner(temp_db, tokenizer, difficulty_scorer=None)
    result = miner.analyze_text("The cat sat. Hello world.", "en")
    assert isinstance(result, MiningResult)
    assert len(result.sentences) >= 1
    for s in result.sentences:
        assert s.difficulty_score is None
        assert s.category is None


def test_miner_with_scorer(temp_db, tokenizer, freq_list):
    """Mining with scorer fills difficulty_score and category."""
    resources = ResourceBundle(language="en", frequency_list=freq_list)
    profile = UserProfile(claimed_level="B1", language="en")
    adapter = make_tokenizer_adapter_from_tokenizer_service(tokenizer)
    recall = make_recall_provider_from_db(temp_db)
    scorer = SentenceDifficultyScorer(adapter, resources, profile, recall_provider=recall)
    miner = SentenceMiner(temp_db, tokenizer, difficulty_scorer=scorer)

    result = miner.analyze_text("The cat sat on the mat.", "en")
    assert len(result.sentences) >= 1
    first = result.sentences[0]
    assert first.difficulty_score is not None
    assert 0 <= first.difficulty_score <= 1
    assert first.category is not None
    assert first.category in (
        "learned", "review", "somewhat_novel", "stretch", "too_advanced"
    )


def test_scores_differ_with_known_words(temp_db, tokenizer, freq_list):
    """Adding a word to known_words lowers difficulty for sentences containing it."""
    resources = ResourceBundle(language="en", frequency_list=freq_list)
    profile = UserProfile(claimed_level="B1", language="en")
    adapter = make_tokenizer_adapter_from_tokenizer_service(tokenizer)
    recall = make_recall_provider_from_db(temp_db)
    scorer = SentenceDifficultyScorer(adapter, resources, profile, recall_provider=recall)
    miner = SentenceMiner(temp_db, tokenizer, difficulty_scorer=scorer)

    text = "The cat sat on the mat."
    result_before = miner.analyze_text(text, "en")
    score_before = result_before.sentences[0].difficulty_score

    temp_db.add_known_word("mat", "en", source="test")
    result_after = miner.analyze_text(text, "en")
    score_after = result_after.sentences[0].difficulty_score

    # After marking "mat" known, difficulty should be lower or equal
    assert score_after <= score_before


def test_get_user_recall_data(temp_db):
    """DB get_user_recall_data returns lemma -> 1.0 for known words."""
    temp_db.add_known_word("hello", "en", source="test")
    temp_db.add_known_word("world", "en", source="test")
    recall = temp_db.get_user_recall_data("en")
    assert recall["hello"] == 1.0
    assert recall["world"] == 1.0
    assert "unknown" not in recall
