"""
Map continuous difficulty score (0-1) to category labels.
Five categories: learned, review, somewhat_novel, stretch, too_advanced.
Thresholds are tunable.
"""

from typing import Tuple

# Default thresholds (can be overridden for calibration)
DEFAULT_THRESHOLDS = (
    0.20,   # learned: score < 0.2
    0.35,   # review: 0.2 <= score < 0.35
    0.65,   # somewhat_novel: 0.35 <= score < 0.65
    0.85,   # stretch: 0.65 <= score < 0.85
    # too_advanced: score >= 0.85
)

CATEGORIES = (
    "learned",
    "review",
    "somewhat_novel",
    "stretch",
    "too_advanced",
)


def score_to_category(
    score: float,
    thresholds: Tuple[float, float, float, float] = DEFAULT_THRESHOLDS,
) -> str:
    """
    Map difficulty score in [0, 1] to one of the 5 categories.
    Higher score = harder. Thresholds: (learned_max, review_max, novel_max, stretch_max).
    """
    if score < 0 or score > 1:
        score = max(0.0, min(1.0, score))
    t1, t2, t3, t4 = thresholds
    if score < t1:
        return "learned"
    if score < t2:
        return "review"
    if score < t3:
        return "somewhat_novel"
    if score < t4:
        return "stretch"
    return "too_advanced"


def score_to_three_category(score: float) -> str:
    """Map to easy / medium / hard (spec-style)."""
    if score < 0.35:
        return "easy"
    if score < 0.65:
        return "medium"
    return "hard"
