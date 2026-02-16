"""
Sentence difficulty scorer: continuous 0-1 score from vocabulary familiarity,
sentence structure, and optional SRS/recall data. Integrates with SentenceMiner.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple, Any

from src.services.text.difficulty_resources import (
    ResourceBundle,
    get_estimated_vocab_size,
    FrequencyList,
    GradedList,
)
from src.services.text.difficulty_categories import score_to_category


# Tokenizer adapter: (text: str, lang_code: str) -> List[str] (lemmas)
TokenizerAdapter = Callable[[str, str], List[str]]

# Recall provider: (lang_code: str) -> Dict[str, float] (lemma -> recall 0-1) or None to use only imputation
RecallProvider = Optional[Callable[[str], Dict[str, float]]]


DEFAULT_WEIGHTS = {
    "mean_recall": 0.20,
    "min_recall": 0.35,
    "unknown_ratio": 0.25,
    "length": 0.10,
    "avg_word_length": 0.05,
    "dep_complexity": 0.05,
}

UNKNOWN_THRESHOLD = 0.75  # Words with < 75% recall prob are treated as "unknown"
STEEPNESS = 0.005
DEFAULT_NON_SRS_RECALL = 0.15  # Default for words not found in freq/graded lists


@dataclass
class SRSRecord:
    """Per-word SRS data (optional; used when recall provider returns probabilities)."""
    word: str
    recall_probability: float
    review_count: int = 0
    interval_days: int = 0


@dataclass
class UserProfile:
    """User context for difficulty scoring."""
    claimed_level: str  # e.g. "B1", "HSK3"
    language: str
    l1_language: Optional[str] = None
    srs_data: Dict[str, SRSRecord] = field(default_factory=dict)


@dataclass
class SentenceScore:
    """Result of scoring one sentence."""
    sentence: str
    difficulty_score: float
    confidence: float
    features: Dict[str, float]
    feature_sources: Dict[str, str]
    bottleneck_word: Optional[str] = None
    unknown_count: int = 0

    @property
    def difficulty_category(self) -> str:
        return score_to_category(self.difficulty_score)


def estimate_recall_probability(
    word_rank: int,
    vocab_size: int,
    steepness: float = STEEPNESS,
) -> float:
    """Sigmoid: P(recall) = 1 / (1 + e^(k*(rank - vocab_size)))."""
    if vocab_size <= 0:
        return 0.5
    try:
        exponent = steepness * (word_rank - vocab_size)
        return 1.0 / (1.0 + math.exp(exponent))
    except OverflowError:
        return 0.0 if word_rank > vocab_size else 1.0


def impute_word_recall(
    word: str,
    user_level: str,
    frequency_list: Optional[FrequencyList],
    graded_list: Optional[GradedList],
) -> Tuple[float, str]:
    """
    Impute recall for a word not in SRS.
    Returns (recall_probability, source) with source in ("sigmoid", "graded", "default").
    """
    if frequency_list:
        rank = frequency_list.get_rank(word)
        if rank is not None:
            vocab_size = get_estimated_vocab_size(user_level)
            prob = estimate_recall_probability(rank, vocab_size)
            return round(prob, 4), "sigmoid"
    if graded_list:
        if graded_list.is_above_level(word, user_level):
            return 0.1, "graded"
        return 0.9, "graded"
    return DEFAULT_NON_SRS_RECALL, "default"


class SentenceDifficultyScorer:
    """
    Scores sentence difficulty 0-1 using tokenizer adapter, resource bundle, and
    optional recall data (known_words -> 1.0 or lemma -> recall).
    """

    def __init__(
        self,
        tokenizer_adapter: TokenizerAdapter,
        resources: ResourceBundle,
        user_profile: UserProfile,
        recall_provider: RecallProvider = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.tokenizer = tokenizer_adapter
        self.resources = resources
        self.user_profile = user_profile
        self.recall_provider = recall_provider
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def score_sentence(self, sentence: str, lang_code: Optional[str] = None) -> SentenceScore:
        """Score a single sentence. lang_code defaults to user_profile.language."""
        lang = lang_code or self.user_profile.language
        tokens = self._tokenize(sentence, lang)
        if not tokens:
            return self._empty_score(sentence)

        recall_by_word, sources = self._get_recalls(tokens, lang)
        recall_probs = [recall_by_word[w] for w in tokens]

        mean_recall = sum(recall_probs) / len(recall_probs)
        min_recall = min(recall_probs)
        unknown_count = sum(1 for p in recall_probs if p < UNKNOWN_THRESHOLD)
        unknown_ratio = unknown_count / len(tokens)

        length_norm = self._normalize_length(len(tokens))
        avg_wlen = sum(len(t) for t in tokens) / len(tokens)
        avg_word_length_norm = self._normalize_word_length(avg_wlen)

        dep_complexity_norm = 0.5  # neutral when no parser
        if self.resources.has_parser and sentence.strip():
            dep_complexity_norm = self._dependency_complexity(sentence)

        # Difficulty = weighted sum with inversion for recall (high recall -> low difficulty)
        raw = {
            "mean_recall": mean_recall,
            "min_recall": min_recall,
            "unknown_ratio": unknown_ratio,
            "length": length_norm,
            "avg_word_length": avg_word_length_norm,
            "dep_complexity": dep_complexity_norm,
        }
        difficulty_score = (
            self.weights.get("mean_recall", 0) * (1.0 - raw["mean_recall"])
            + self.weights.get("min_recall", 0) * (1.0 - raw["min_recall"])
            + self.weights.get("unknown_ratio", 0) * raw["unknown_ratio"]
            + self.weights.get("length", 0) * raw["length"]
            + self.weights.get("avg_word_length", 0) * raw["avg_word_length"]
            + self.weights.get("dep_complexity", 0) * raw["dep_complexity"]
        )
        difficulty_score = round(max(0.0, min(1.0, difficulty_score)), 4)

        confidence = self._confidence(sources)
        bottleneck_word = min(
            (w for w in tokens),
            key=lambda w: recall_by_word[w],
            default=None,
        ) if tokens else None

        return SentenceScore(
            sentence=sentence,
            difficulty_score=difficulty_score,
            confidence=round(confidence, 4),
            features=raw,
            feature_sources=dict(sources),
            bottleneck_word=bottleneck_word,
            unknown_count=unknown_count,
        )

    def score_batch(
        self,
        sentences: List[str],
        lang_code: Optional[str] = None,
        show_progress: bool = False,
        precomputed_recall: Optional[Dict[str, float]] = None,
    ) -> List[SentenceScore]:
        """
        Score multiple sentences efficiently by pre-calculating recall for all tokens.
        """
        lang = lang_code or self.user_profile.language
        
        # 1. First pass: Tokenize all and collect unique lemmas
        all_tokens_per_sent = [self._tokenize(s, lang) for s in sentences]
        unique_lemmas = set()
        for tokens in all_tokens_per_sent:
            unique_lemmas.update(w.lower() for w in tokens)
        
        # 2. Fetch recall data for all unique lemmas at once
        batch_recall, batch_sources = self._get_batch_recalls(list(unique_lemmas), lang, precomputed_recall)
        
        # 3. Score each sentence using the pre-calculated data
        out = []
        for i, sentence in enumerate(sentences):
            tokens = all_tokens_per_sent[i]
            if not tokens:
                out.append(self._empty_score(sentence))
                continue
            
            # Extract local recall slice
            local_recall = {t: batch_recall[t.lower()] for t in tokens}
            local_sources = {t: batch_sources[t.lower()] for t in tokens}
            
            # Perform scoring (reusing most of score_sentence logic but avoiding re-fetching)
            out.append(self._score_with_data(sentence, tokens, local_recall, local_sources))
            
        return out

    def _get_batch_recalls(
        self, lemmas: List[str], lang_code: str, precomputed: Optional[Dict[str, float]] = None
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        recall_map = {}
        source_map = {}
        user_recall = precomputed
        if user_recall is None and self.recall_provider:
            user_recall = self.recall_provider(lang_code)
            
        for key in lemmas:
            if self.user_profile.srs_data and key in self.user_profile.srs_data:
                recall_map[key] = self.user_profile.srs_data[key].recall_probability
                source_map[key] = "srs"
            elif user_recall is not None and key in user_recall:
                recall_map[key] = user_recall[key]
                source_map[key] = "srs"
            else:
                prob, src = impute_word_recall(
                    key,
                    self.user_profile.claimed_level,
                    self.resources.frequency_list,
                    self.resources.graded_list,
                )
                recall_map[key] = prob
                source_map[key] = src
        return recall_map, source_map

    def _score_with_data(
        self, sentence: str, tokens: List[str], recall_by_word: Dict[str, float], sources: Dict[str, str]
    ) -> SentenceScore:
        """Internal helper for score_sentence/score_batch."""
        recall_probs = [recall_by_word[w] for w in tokens]

        mean_recall = sum(recall_probs) / len(recall_probs)
        min_recall = min(recall_probs)
        unknown_count = sum(1 for p in recall_probs if p < UNKNOWN_THRESHOLD)
        unknown_ratio = unknown_count / len(tokens)

        length_norm = self._normalize_length(len(tokens))
        avg_wlen = sum(len(t) for t in tokens) / len(tokens)
        avg_word_length_norm = self._normalize_word_length(avg_wlen)

        dep_complexity_norm = 0.5
        if self.resources.has_parser and sentence.strip():
            dep_complexity_norm = self._dependency_complexity(sentence)

        raw = {
            "mean_recall": mean_recall,
            "min_recall": min_recall,
            "unknown_ratio": unknown_ratio,
            "length": length_norm,
            "avg_word_length": avg_word_length_norm,
            "dep_complexity": dep_complexity_norm,
        }
        
        difficulty_score = (
            self.weights.get("mean_recall", 0) * (1.0 - raw["mean_recall"])
            + self.weights.get("min_recall", 0) * (1.0 - raw["min_recall"])
            + self.weights.get("unknown_ratio", 0) * raw["unknown_ratio"]
            + self.weights.get("length", 0) * raw["length"]
            + self.weights.get("avg_word_length", 0) * raw["avg_word_length"]
            + self.weights.get("dep_complexity", 0) * raw["dep_complexity"]
        )
        difficulty_score = round(max(0.0, min(1.0, difficulty_score)), 4)

        return SentenceScore(
            sentence=sentence,
            difficulty_score=difficulty_score,
            confidence=round(self._confidence(sources), 4),
            features=raw,
            feature_sources=dict(sources),
            bottleneck_word=min(tokens, key=lambda w: recall_by_word[w]) if tokens else None,
            unknown_count=unknown_count,
        )

    def _tokenize(self, text: str, lang_code: str) -> List[str]:
        """Return list of lemmas (strings) for content tokens only."""
        raw = self.tokenizer(text, lang_code)
        # Filter to word-like tokens (skip empty and pure punctuation)
        return [t for t in raw if t and any(c.isalnum() for c in t)]

    def _get_recalls(self, tokens: List[str], lang_code: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        recall_by_word: Dict[str, float] = {}
        sources: Dict[str, str] = {}
        user_recall: Optional[Dict[str, float]] = None
        if self.recall_provider:
            user_recall = self.recall_provider(lang_code)
        for w in tokens:
            key = w.lower()
            if self.user_profile.srs_data and key in self.user_profile.srs_data:
                rec = self.user_profile.srs_data[key].recall_probability
                recall_by_word[w] = rec
                sources[w] = "srs"
            elif user_recall is not None and key in user_recall:
                recall_by_word[w] = user_recall[key]
                sources[w] = "srs"
            else:
                prob, src = impute_word_recall(
                    key,
                    self.user_profile.claimed_level,
                    self.resources.frequency_list,
                    self.resources.graded_list,
                )
                recall_by_word[w] = prob
                sources[w] = src
        return recall_by_word, sources

    def _normalize_length(self, token_count: int) -> float:
        if self.resources.has_quantile_buckets:
            return self.resources.quantile_buckets.normalize(float(token_count), "length")
        return min(1.0, token_count / 30.0)

    def _normalize_word_length(self, avg_chars: float) -> float:
        if self.resources.has_quantile_buckets:
            return self.resources.quantile_buckets.normalize(avg_chars, "word_length")
        return min(1.0, avg_chars / 8.0)

    def _dependency_complexity(self, sentence: str) -> float:
        try:
            doc = self.resources.parser(sentence)
            distances = []
            for token in doc:
                if token.head != token:
                    distances.append(abs(token.i - token.head.i))
            if not distances:
                return 0.5
            avg = sum(distances) / len(distances)
            if self.resources.has_quantile_buckets:
                return self.resources.quantile_buckets.normalize(avg, "dep_complexity")
            return min(1.0, avg / 5.0)
        except Exception:
            return 0.5

    def _confidence(self, sources: Dict[str, str]) -> float:
        by_source = {"srs": 1.0, "sigmoid": 0.7, "graded": 0.5, "default": 0.3}
        if not sources:
            return 0.3
        total = sum(by_source.get(s, 0.3) for s in sources.values())
        return total / len(sources)

    def _empty_score(self, sentence: str) -> SentenceScore:
        return SentenceScore(
            sentence=sentence,
            difficulty_score=0.5,
            confidence=0.0,
            features={
                "mean_recall": 0.5,
                "min_recall": 0.5,
                "unknown_ratio": 0.0,
                "length": 0.0,
                "avg_word_length": 0.5,
                "dep_complexity": 0.5,
            },
            feature_sources={},
            bottleneck_word=None,
            unknown_count=0,
        )


def make_tokenizer_adapter_from_tokenizer_service(tokenizer_service: Any) -> TokenizerAdapter:
    """
    Build a TokenizerAdapter from the project's TokenizerService.
    Returns (text, lang_code) -> list of lemma strings.
    """
    def adapter(text: str, lang_code: str) -> List[str]:
        tokens = tokenizer_service.tokenize(text, lang_code)
        return [t.lemma or t.text for t in tokens]
    return adapter


def make_recall_provider_from_db(db: Any) -> RecallProvider:
    """
    Build a recall provider from FlashcardDatabase: known_words -> 1.0, others imputed.
    Uses db.get_user_recall_data(lang_code) when available.
    Returns a callable (lang_code: str) -> Dict[str, float].
    """
    def provider(lang_code: str) -> Dict[str, float]:
        if hasattr(db, "get_user_recall_data"):
            return db.get_user_recall_data(lang_code)
        words = db.get_all_known_words(lang_code)
        return {w["lemma"].lower(): 1.0 for w in words}
    return provider
