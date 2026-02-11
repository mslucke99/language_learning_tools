from typing import List, Dict, Optional
from .tokenizer_service import TokenizerService, Token
from ..dictionary.dictionary_manager import DictionaryEngine

class TextAnalysisService:
    """
    High-level service to analyze text.
    Combines Tokenization + Dictionary Lookups.
    """
    def __init__(self, dictionary_engine: DictionaryEngine):
        self.tokenizer = TokenizerService()
        self.dictionary = dictionary_engine

    def analyze_sentence(self, text: str, lang_code: str) -> List[Dict]:
        """
        Tokenizes the sentence and looks up each token in the dictionary.
        Returns a list of token objects with an added 'definitions' field.
        """
        tokens = self.tokenizer.tokenize(text, lang_code)
        
        analyzed_tokens = []
        for token in tokens:
            token_data = token.to_dict()
            
            # Look up the lemma (base form)
            definitions = self.dictionary.lookup(token.lemma, lang_code)
            
            # If no definitions for lemma, try the raw text
            if not definitions and token.text != token.lemma:
                definitions = self.dictionary.lookup(token.text, lang_code)
                
            token_data['definitions'] = definitions
            analyzed_tokens.append(token_data)
            
        return analyzed_tokens

    def get_token_definition(self, token_text: str, lang_code: str) -> Optional[Dict]:
        """
        Simple helper to look up a single token.
        """
        results = self.dictionary.lookup(token_text, lang_code)
        return results[0] if results else None
