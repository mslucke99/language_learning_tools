"""
Resource loading for sentence difficulty scoring.
Reuses vocab_calibration cache paths for frequency lists; supports optional graded lists and quantiles.
"""
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# Vocabulary size estimates for sigmoid imputation (aligned with spec; B1=2500).
# For calibration seeding the app uses VocabCalibrationService.LEVEL_COUNTS (B1=3000).
VOCAB_SIZE_MAP = {
    "A1": 500,
    "A2": 1200,
    "B1": 2500,
    "B2": 5000,
    "C1": 10000,
    "C2": 20000,
    "ABSOLUTE_BEGINNER": 0,
    "INTRODUCTORY": 100,
    "HSK1": 150,
    "HSK2": 300,
    "HSK3": 600,
    "HSK4": 1200,
    "HSK5": 2500,
    "HSK6": 5000,
    "TOPIK1": 800,
    "TOPIK2": 1500,
    "TOPIK3": 2500,
    "TOPIK4": 4000,
    "TOPIK5": 6000,
    "TOPIK6": 10000,
    "N5": 800,
    "N4": 1500,
    "N3": 3000,
    "N2": 6000,
    "N1": 10000,
}


def get_estimated_vocab_size(level: str) -> int:
    """Estimated vocabulary size for a proficiency level (sigmoid center)."""
    key = level.upper() if level else ""
    return VOCAB_SIZE_MAP.get(key, 1000)


class FrequencyList:
    """Word frequency data: word -> rank (1 = most common)."""

    def __init__(self, word_to_rank: Dict[str, int], total_words: int):
        self.word_to_rank = word_to_rank
        self.total_words = max(total_words, len(word_to_rank)) if word_to_rank else 0

    def get_rank(self, word: str) -> Optional[int]:
        return self.word_to_rank.get(word.lower())

    def get_rarity_score(self, word: str) -> float:
        """0-1, higher = rarer."""
        rank = self.get_rank(word)
        if rank is None:
            return 1.0
        if self.total_words <= 0:
            return 0.5
        import math
        return math.log(rank + 1) / math.log(self.total_words + 1)

    @classmethod
    def load_from_words(cls, words: List[str]) -> "FrequencyList":
        """Build from ordered list of words (rank = 1-based index)."""
        word_to_rank = {w.lower(): i for i, w in enumerate(words, start=1)}
        return cls(word_to_rank, len(words))

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["FrequencyList"]:
        """Load from file: one word per line, or word\\trank."""
        if not os.path.exists(filepath):
            return None
        word_to_rank = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                word = parts[0].strip().lower()
                rank = int(parts[1]) if len(parts) > 1 else idx
                word_to_rank[word] = rank
        total = max(word_to_rank.values()) if word_to_rank else 0
        return cls(word_to_rank, total)


class GradedList:
    """CEFR/HSK/TOPIK/JLPT word -> level."""

    def __init__(self, word_to_level: Dict[str, str], framework: str):
        self.word_to_level = word_to_level
        self.framework = framework
        self._level_order = self._level_order_for_framework(framework)

    def _level_order_for_framework(self, framework: str) -> List[str]:
        if framework == "CEFR":
            return ["A1", "A2", "B1", "B2", "C1", "C2"]
        if framework == "HSK":
            return ["HSK1", "HSK2", "HSK3", "HSK4", "HSK5", "HSK6"]
        if framework == "TOPIK":
            return ["TOPIK1", "TOPIK2", "TOPIK3", "TOPIK4", "TOPIK5", "TOPIK6"]
        if framework == "JLPT":
            return ["N5", "N4", "N3", "N2", "N1"]
        return []

    def get_level(self, word: str) -> Optional[str]:
        return self.word_to_level.get(word.lower())

    def get_level_number(self, level: str) -> int:
        try:
            return self._level_order.index(level)
        except ValueError:
            return -1

    def is_above_level(self, word: str, user_level: str) -> bool:
        word_level = self.get_level(word)
        if word_level is None:
            return True
        wn = self.get_level_number(word_level)
        un = self.get_level_number(user_level)
        return wn > un if un >= 0 else True

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["GradedList"]:
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        framework = data.get("framework", "CEFR")
        words = data.get("words", {})
        words = {k.lower(): v for k, v in words.items()}
        return cls(words, framework)


class QuantileBuckets:
    """Quantile-based normalization for length, word_length, dep_complexity."""

    def __init__(self, quantiles: Dict[str, Dict[float, float]]):
        self.quantiles = quantiles

    def normalize(self, value: float, feature_name: str) -> float:
        if feature_name not in self.quantiles:
            return min(1.0, value / 10.0)
        buckets = self.quantiles[feature_name]
        qs = sorted(buckets.keys())
        for q in qs:
            if value <= buckets[q]:
                return q
        return 1.0

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["QuantileBuckets"]:
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("quantiles", {})
        converted = {}
        for name, d in raw.items():
            converted[name] = {float(k): v for k, v in d.items()}
        return cls(converted)


@dataclass
class ResourceBundle:
    """Container for language resources used by the difficulty scorer."""

    language: str
    frequency_list: Optional[FrequencyList] = None
    graded_list: Optional[GradedList] = None
    quantile_buckets: Optional[QuantileBuckets] = None
    parser: Any = None

    @property
    def has_frequency_list(self) -> bool:
        return self.frequency_list is not None

    @property
    def has_graded_list(self) -> bool:
        return self.graded_list is not None

    @property
    def has_quantile_buckets(self) -> bool:
        return self.quantile_buckets is not None

    @property
    def has_parser(self) -> bool:
        return self.parser is not None


# Same as VocabCalibrationService for compatibility
LANG_MAP = {
    "ko": "ko",
    "es": "es",
    "fr": "fr",
    "ja": "ja",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "zh": "zh-CN",
}


def get_frequency_list_cache_dir(db_path: str) -> str:
    """Same cache dir as VocabCalibrationService."""
    return os.path.join(os.path.dirname(db_path), "cache", "frequency_lists")


def get_graded_list_dir(db_path: str) -> str:
    """Directory for graded vocabulary JSON files."""
    return os.path.join(os.path.dirname(db_path), "cache", "graded_vocabularies")


def get_quantile_dir(db_path: str) -> str:
    """Directory for quantile bucket JSON files."""
    return os.path.join(os.path.dirname(db_path), "cache", "quantile_buckets")


def load_resource_bundle(
    language: str,
    db_path: str,
    load_frequency: bool = True,
    load_graded: bool = False,
    load_quantiles: bool = False,
    load_parser: bool = False,
) -> ResourceBundle:
    """
    Build a ResourceBundle for the given language.
    Uses same frequency list cache as VocabCalibrationService.
    """
    bundle = ResourceBundle(language=language)
    mapped = LANG_MAP.get(language, language)

    if load_frequency:
        cache_dir = get_frequency_list_cache_dir(db_path)
        os.makedirs(cache_dir, exist_ok=True)
        freq_path = os.path.join(cache_dir, f"{mapped}.txt")
        bundle.frequency_list = FrequencyList.load_from_file(freq_path)
        if bundle.frequency_list is None and language != mapped:
            alt = os.path.join(cache_dir, f"{language}.txt")
            bundle.frequency_list = FrequencyList.load_from_file(alt)

    if load_graded:
        graded_dir = get_graded_list_dir(db_path)
        # Try language-specific file, e.g. en_cefr.json, zh_hsk.json
        for name in [f"{mapped}_cefr.json", f"{mapped}_graded.json", f"{language}_graded.json"]:
            path = os.path.join(graded_dir, name)
            bundle.graded_list = GradedList.load_from_file(path)
            if bundle.graded_list is not None:
                break

    if load_quantiles:
        quant_dir = get_quantile_dir(db_path)
        path = os.path.join(quant_dir, f"{mapped}_quantiles.json")
        bundle.quantile_buckets = QuantileBuckets.load_from_file(path)
        if bundle.quantile_buckets is None:
            path = os.path.join(quant_dir, f"{language}_quantiles.json")
            bundle.quantile_buckets = QuantileBuckets.load_from_file(path)

    if load_parser:
        try:
            import spacy
            model_map = {
                "en": "en_core_web_sm",
                "es": "es_core_news_sm",
                "de": "de_core_news_sm",
                "fr": "fr_core_news_sm",
                "zh": "zh_core_web_sm",
                "zh-CN": "zh_core_web_sm",
                "ja": "ja_core_news_sm",
            }
            model = model_map.get(mapped) or model_map.get(language)
            if model:
                bundle.parser = spacy.load(model)
        except Exception:
            pass

    return bundle
