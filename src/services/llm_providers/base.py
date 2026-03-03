from abc import ABC, abstractmethod
from typing import List, Optional, Dict

class LLMProvider(ABC):
    """
    Abstract base class for all LLM backends.
    All providers must implement these methods to be used by the StudyManager.
    """
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is reachable and configured correctly."""
        pass
    
    @abstractmethod
    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """
        Send a prompt to the LLM and return the generated text.
        Returns None if the request fails.
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Fetch models available through this provider."""
        pass
    
    @abstractmethod
    def set_model(self, model_name: str) -> bool:
        """Configure which specific model to use."""
        pass

    @abstractmethod
    def get_current_model(self) -> Optional[str]:
        """Return the name of the currently selected model."""
        pass

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate mathematical embeddings for a list of strings.
        Returns a list of vectors (lists of floats).
        """
        pass

    def preload_model(self, model_name: str = None) -> bool:
        """
        Optional: Pre-load the model into memory. 
        Defaults to doing nothing if not supported by provider.
        """
        return True
