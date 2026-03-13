from typing import List, Optional
from src.services.llm_providers.base import LLMProvider
import numpy as np

class LocalEmbeddingProvider(LLMProvider):
    """
    Fallback provider for generating embeddings locally.
    Tries sentence-transformers first, then scikit-learn (TF-IDF).
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        import os
        self.model_name = model_name
        self._st_model = None
        
        # Check for local model directory to avoid HF Hub requests
        # We prioritize models/embedding/<model_name>
        self.local_path = os.path.join("models", "embedding", model_name)
        if os.path.isdir(self.local_path):
            print(f"[LocalEmbeddings] Using local model path: {self.local_path}")
            self.model_to_load = self.local_path
        else:
            self.model_to_load = self.model_name

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
        # Reset model loading path if changed
        import os
        self.local_path = os.path.join("models", "embedding", model_name)
        self.model_to_load = self.local_path if os.path.isdir(self.local_path) else model_name
        self._st_model = None
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
                # Load from local_path if exists, otherwise model_name (HF Hub)
                self._st_model = SentenceTransformer(self.model_to_load)
            
            embeddings = self._st_model.encode(texts)
            return embeddings.tolist()
        except ImportError:
            print("[LocalEmbeddings] Error: sentence-transformers not installed.")
            return []
        except Exception as e:
            print(f"[LocalEmbeddings] Error: {e}")
            return []
