from typing import List, Optional
from src.services.llm_providers.base import LLMProvider
import numpy as np

class LocalEmbeddingProvider(LLMProvider):
    """
    Fallback provider for generating embeddings locally.
    Tries sentence-transformers first, then scikit-learn (TF-IDF).
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._st_model = None
        self._tfidf_vectorizer = None
        
    def is_available(self) -> bool:
        """Check if sentence-transformers is installed."""
        import importlib.util
        return importlib.util.find_spec("sentence_transformers") is not None

    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        return None # Not a text generation provider

    def get_available_models(self) -> List[str]:
        return [self.model_name]

    def set_model(self, model_name: str) -> bool:
        self.model_name = model_name
        return True

    def get_current_model(self) -> Optional[str]:
        return self.model_name

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        # Use sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            if not self._st_model:
                self._st_model = SentenceTransformer(self.model_name)
            
            embeddings = self._st_model.encode(texts)
            return embeddings.tolist()
        except ImportError:
            print("[LocalEmbeddings] Error: sentence-transformers not installed.")
            return []
        except Exception as e:
            print(f"[LocalEmbeddings] Error: {e}")
            return []
