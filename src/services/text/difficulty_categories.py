"""
Map continuous difficulty score (0-1) to category labels.
Five categories: learned, review, somewhat_novel, stretch, too_advanced.
Thresholds are tunable.
"""

from typing import Tuple

# Default thresholds (can be overridden for calibration)
DEFAULT_THRESHOLDS = (
    0.15,   # mastered: score < 0.15
    0.35,   # review: 0.15 <= score < 0.35
    0.60,   # sweet_spot: 0.35 <= score < 0.60 (Target i+1 Zone)
    0.85,   # stretch: 0.60 <= score < 0.85
    # too_hard: score >= 0.85
)

CATEGORIES = {
    "mastered": {
        "display": "Mastered",
        "desc": "i+0: You know all these words perfectly. Good for speed reading.",
        "color": "#808080", # Gray
    },
    "review": {
        "display": "Review",
        "desc": "Reinforcement: Contains words you've seen but might need to refresh.",
        "color": "#4CAF50", # Green
    },
    "sweet_spot": {
        "display": "Sweet Spot",
        "desc": "i+1: The ideal challenge. One or two new words in a familiar context.",
        "color": "#2196F3", # Blue
    },
    "stretch": {
        "display": "Stretch",
        "desc": "Challenging: Several new words or complex grammar. Good for intensive study.",
        "color": "#FF9800", # Orange
    },
    "too_hard": {
        "display": "Too Hard",
        "desc": "Too many unknowns. Save this for when you're more advanced.",
        "color": "#F44336", # Red
    },
}


def score_to_category(
    score: float,
    thresholds: Tuple[float, float, float, float] = DEFAULT_THRESHOLDS,
) -> str:
    """
    Map difficulty score in [0, 1] to one of the 5 category keys.
    Higher score = harder. Thresholds: (mastered_max, review_max, sweet_max, stretch_max).
    """
    if score < 0 or score > 1:
        score = max(0.0, min(1.0, score))
    t1, t2, t3, t4 = thresholds
    if score < t1:
        return "mastered"
    if score < t2:
        return "review"
    if score < t3:
        return "sweet_spot"
    if score < t4:
        return "stretch"
    return "too_hard"


def score_to_three_category(score: float) -> str:
    """Map to easy / medium / hard (spec-style)."""
    if score < 0.35:
        return "easy"
    if score < 0.65:
        return "medium"
    return "hard"
