import pytest
import numpy as np
from src.services.text.semantic_familiarity import SemanticFamiliarityScorer, ClusterProfile
from src.services.text.sentence_difficulty import SentenceDifficultyScorer, SentenceScore

def test_high_familiarity_near_cluster():
    # Setup a strong cluster at [1, 0, 0]
    profiles = [
        ClusterProfile(
            centroid=np.array([1.0, 0.0, 0.0]),
            strength=1.0,
            sample_words=["test"]
        )
    ]
    scorer = SemanticFamiliarityScorer(profiles)
    
    # Word right on the centroid
    word_embeddings = [[1.0, 0.0, 0.0]]
    score = scorer.score_words(word_embeddings)
    assert score > 0.9 # Should be very high

def test_low_familiarity_far_from_clusters():
    # Cluster at [1, 0, 0]
    profiles = [
        ClusterProfile(
            centroid=np.array([1.0, 0.0, 0.0]),
            strength=1.0,
            sample_words=["test"]
        )
    ]
    scorer = SemanticFamiliarityScorer(profiles)
    
    # Word orthogonal to centroid ([0, 1, 0] -> cosine sim 0)
    word_embeddings = [[0.0, 1.0, 0.0]]
    score = scorer.score_words(word_embeddings)
    assert score < 0.1 # Should be very low

def test_empty_clusters_returns_neutral():
    scorer = SemanticFamiliarityScorer([])
    assert scorer.score_words([[1, 0]]) == 0.5

def test_reweight_with_semantics(tokenizer_adapter, resources_with_frequency, user_profile):
    scorer = SentenceDifficultyScorer(
        tokenizer_adapter, resources_with_frequency, user_profile
    )
    
    # Create a base score (all known to keep it simple)
    # The actual calculation depends on weights, but let's check relative change
    original_score = SentenceScore(
        sentence="Test sentence",
        difficulty_score=0.2, # Baseline
        confidence=1.0,
        features={
            "mean_recall": 1.0,
            "min_recall": 1.0,
            "unknown_ratio": 0.0,
            "length": 0.2,
            "avg_word_length": 0.2,
            "dep_complexity": 0.2
        },
        feature_sources={},
        bottleneck_word=None,
        unknown_count=0
    )
    
    # High familiarity (1.0) -> should lower difficulty
    easier_score = scorer.reweight_with_semantics(original_score, 1.0)
    assert easier_score.difficulty_score < original_score.difficulty_score
    
    # Low familiarity (0.0) -> should raise difficulty
    harder_score = scorer.reweight_with_semantics(original_score, 0.0)
    assert harder_score.difficulty_score > easier_score.difficulty_score
