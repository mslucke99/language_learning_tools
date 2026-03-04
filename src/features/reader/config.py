"""
Configuration settings for Adventure Graded Reader.

This module provides default configuration values and initialization
settings for the reader feature.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ReaderConfig:
    """
    Configuration for Adventure Graded Reader.
    
    Attributes:
        min_coverage: Minimum vocabulary coverage required (default 0.95 = 95%)
        max_new_words: Maximum new words per passage (default 2)
        min_vocabulary_size: Minimum known words required to start (default 50)
        llm_timeout: Timeout for LLM requests in seconds (default 60)
        llm_max_retries: Maximum LLM retry attempts (default 3)
        db_reconnect_attempts: Database reconnection attempts (default 3)
        cache_templates: Whether to cache templates in memory (default True)
        cache_vocabulary: Whether to cache vocabulary in memory (default True)
    """
    
    # Vocabulary constraints
    min_coverage: float = 0.95
    max_new_words: int = 2
    min_vocabulary_size: int = 50
    
    # LLM settings
    llm_timeout: int = 60
    llm_max_retries: int = 3
    
    # Database settings
    db_reconnect_attempts: int = 3
    
    # Performance settings
    cache_templates: bool = True
    cache_vocabulary: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'min_coverage': self.min_coverage,
            'max_new_words': self.max_new_words,
            'min_vocabulary_size': self.min_vocabulary_size,
            'llm_timeout': self.llm_timeout,
            'llm_max_retries': self.llm_max_retries,
            'db_reconnect_attempts': self.db_reconnect_attempts,
            'cache_templates': self.cache_templates,
            'cache_vocabulary': self.cache_vocabulary,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReaderConfig':
        """Create config from dictionary."""
        return cls(**data)
    
    def validate(self) -> bool:
        """
        Validate configuration values.
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not (0.0 <= self.min_coverage <= 1.0):
            return False
        
        if not (1 <= self.max_new_words <= 3):
            return False
        
        if self.min_vocabulary_size < 10:
            return False
        
        if self.llm_timeout < 10:
            return False
        
        if self.llm_max_retries < 1:
            return False
        
        if self.db_reconnect_attempts < 1:
            return False
        
        return True


# Default configuration instance
DEFAULT_CONFIG = ReaderConfig()


# Language-specific tokenization settings
LANGUAGE_TOKENIZERS = {
    'korean': {
        'library': 'konlpy',
        'tokenizer': 'Okt',
        'requires_install': True
    },
    'japanese': {
        'library': 'spacy',
        'model': 'ja_core_news_sm',
        'requires_install': True
    },
    'spanish': {
        'library': 'spacy',
        'model': 'es_core_news_sm',
        'requires_install': True
    },
    'english': {
        'library': 'spacy',
        'model': 'en_core_web_sm',
        'requires_install': True
    },
    'chinese': {
        'library': 'spacy',
        'model': 'zh_core_web_sm',
        'requires_install': True
    },
}


def get_tokenizer_config(language: str) -> Dict[str, Any]:
    """
    Get tokenizer configuration for a language.
    
    Args:
        language: Target language
    
    Returns:
        Dict with tokenizer configuration
    """
    return LANGUAGE_TOKENIZERS.get(language.lower(), {
        'library': 'simple',
        'requires_install': False
    })


def is_tokenizer_available(language: str) -> bool:
    """
    Check if tokenizer is available for a language.
    
    Args:
        language: Target language
    
    Returns:
        bool: True if tokenizer is available
    """
    config = get_tokenizer_config(language)
    
    if config.get('library') == 'simple':
        return True
    
    try:
        if config.get('library') == 'spacy':
            import spacy
            model = config.get('model')
            try:
                spacy.load(model)
                return True
            except OSError:
                return False
        
        elif config.get('library') == 'konlpy':
            from konlpy.tag import Okt
            return True
    
    except ImportError:
        return False
    
    return False
