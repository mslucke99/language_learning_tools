"""
Unit tests for sentence difficulty: imputation, categories, and scorer.
"""
import os
import tempfile
import pytest

from src.services.text.difficulty_resources import (
    get_estimated_vocab_size,
    FrequencyList,
    GradedList,
    ResourceBundle,
)
from src.services.text.sentence_difficulty import (
    estimate_recall_probability as sigmoid_estimate,
    impute_word_recall,
    UserProfile,
    SentenceDifficultyScorer,
    SentenceScore,
)
from src.services.text.difficulty_categories import score_to_category, score_to_three_category


# Use difficulty_resources for get_estimated_vocab_size and FrequencyList/GradedList
# sentence_difficulty re-exports estimate_recall_probability - use the one in sentence_difficulty for consistency
def _sigmoid(rank: int, vocab: int, k: float = 0.005) -> float:
    return sigmoid_estimate(rank, vocab, k)


class TestSigmoidImputation:
    def test_center_point(self):
        p = _sigmoid(2500, 2500)
        assert abs(p - 0.5) < 0.01

    def test_common_word(self):
        p = _sigmoid(100, 2500)
        assert p > 0.95

    def test_rare_word(self):
        p = _sigmoid(10000, 2500)
        assert p < 0.05

    def test_monotonicity(self):
        vocab = 2500
        ranks = [100, 500, 1000, 2500, 5000, 10000]
        probs = [_sigmoid(r, vocab) for r in ranks]
        assert all(probs[i] > probs[i + 1] for i in range(len(probs) - 1))

    def test_overflow_handling(self):
        p = _sigmoid(1000000, 2500)
        assert p == 0.0


class TestVocabularySize:
    def test_cefr_levels(self):
        assert get_estimated_vocab_size("A1") == 500
        assert get_estimated_vocab_size("A2") == 1200
        assert get_estimated_vocab_size("B1") == 2500
        assert get_estimated_vocab_size("B2") == 5000
        assert get_estimated_vocab_size("C2") == 20000

    def test_unknown_level(self):
        assert get_estimated_vocab_size("UNKNOWN") == 1000


class TestImputeWordRecall:
    def test_sigmoid_imputation(self):
        freq = FrequencyList({"the": 1, "cat": 200, "photosynthesis": 8000}, 10000)
        prob, source = impute_word_recall("cat", "B1", freq, None)
        assert source == "sigmoid"
        assert 0.85 < prob <= 1.0

    def test_graded_fallback(self):
        graded = GradedList({"hello": "A1", "important": "B1"}, "CEFR")
        prob, source = impute_word_recall("important", "B1", None, graded)
        assert source == "graded"
        assert prob == 0.9

    def test_default_fallback(self):
        prob, source = impute_word_recall("unknown", "B1", None, None)
        assert source == "default"
        assert prob == 0.15


class TestDifficultyCategories:
    def test_five_categories(self):
        assert score_to_category(0.1) == "mastered"
        assert score_to_category(0.25) == "review"
        assert score_to_category(0.5) == "sweet_spot"
        assert score_to_category(0.75) == "stretch"
        assert score_to_category(0.9) == "too_hard"

    def test_boundaries(self):
        assert score_to_category(0.20) == "review"
        assert score_to_category(0.35) == "sweet_spot"
        assert score_to_category(0.65) == "stretch"
        assert score_to_category(0.85) == "too_hard"

    def test_three_category(self):
        assert score_to_three_category(0.2) == "easy"
        assert score_to_three_category(0.5) == "medium"
        assert score_to_three_category(0.8) == "hard"


class TestSentenceDifficultyScorer:
    def test_empty_sentence(self, tokenizer_adapter, empty_resources, user_profile):
        scorer = SentenceDifficultyScorer(tokenizer_adapter, empty_resources, user_profile)
        result = scorer.score_sentence("")
        assert result.difficulty_score == 0.5
        assert result.confidence == 0.0

    def test_single_word(self, tokenizer_adapter, resources_with_frequency, user_profile):
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter, resources_with_frequency, user_profile
        )
        result = scorer.score_sentence("the")
        assert 0 <= result.difficulty_score <= 1
        assert result.difficulty_category in (
            "mastered", "review", "sweet_spot", "stretch", "too_hard"
        )

    def test_easy_sentence(self, tokenizer_adapter, resources_with_frequency, user_profile):
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter, resources_with_frequency, user_profile
        )
        result = scorer.score_sentence("The cat sat on the mat.")
        assert result.difficulty_score < 0.5
        assert result.bottleneck_word is not None

    def test_batch(self, tokenizer_adapter, empty_resources, user_profile):
        scorer = SentenceDifficultyScorer(tokenizer_adapter, empty_resources, user_profile)
        results = scorer.score_batch(["Hello.", "World."])
        assert len(results) == 2
        assert all(isinstance(r, SentenceScore) for r in results)
        assert all(0 <= r.difficulty_score <= 1 for r in results)

    def test_determinism(self, tokenizer_adapter, resources_with_frequency, user_profile):
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter, resources_with_frequency, user_profile
        )
        r1 = scorer.score_sentence("The cat sat.")
        r2 = scorer.score_sentence("The cat sat.")
        assert r1.difficulty_score == r2.difficulty_score
        assert r1.confidence == r2.confidence

    def test_all_known_discount(self, tokenizer_adapter, resources_with_frequency, user_profile):
        """Verify structural discount applies when all words are known."""
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter, resources_with_frequency, user_profile
        )
        # All words in freq list (1.0 recall for 'the', 'cat', 'sat')
        # We manually set recall to 1.0 via provider to be sure
        scorer.recall_provider = lambda lang: {"the": 1.0, "cat": 1.0, "sat": 1.0}
        
        result = scorer.score_sentence("The cat sat.")
        # Without discount, a 3-word sentence might be around 0.1-0.2
        # With 0.3x discount, it should be very low
        assert result.difficulty_score < 0.1
        assert result.difficulty_category == "mastered"

    def test_no_discount_for_unknowns(self, tokenizer_adapter, resources_with_frequency, user_profile):
        """Verify structural discount does NOT apply when there are unknowns."""
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter, resources_with_frequency, user_profile
        )
        # 'unknownword' is not in freq list, will have low recall (0.15)
        result = scorer.score_sentence("The cat unknownword.")
        assert result.unknown_count >= 1
        # Score should be significantly higher than mastered
        assert result.difficulty_score > 0.15
        assert result.difficulty_category != "mastered"
