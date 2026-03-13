"""
Unified LLM Service for grammar explanations and word definitions.
Supports multiple providers including Ollama, OpenAI, and Gemini.
"""

from typing import Optional, Dict, List, Type
import threading

# Import Providers
from src.services.llm_providers.base import LLMProvider
from src.services.llm_providers.ollama_provider import OllamaProvider
from src.services.llm_providers.openai_compatible import OpenAICompatibleProvider
from src.services.llm_providers.gemini_provider import GeminiProvider
from src.services.llm_providers.security import KeyringManager
from src.services.llm_providers.local_embeddings import LocalEmbeddingProvider
from src.core.config import config as app_config

class LLMService:
    """Unified service for AI-powered language learning assistance."""
    
    def __init__(self, provider_type: str = None, config: Dict = None):
        self.provider_type = provider_type or app_config.llm_provider
        self.config = config or {
            "base_url": app_config.llm_base_url,
            "model": app_config.llm_model
        }
        self.security = KeyringManager()
        self.provider: Optional[LLMProvider] = None
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the specific provider based on configuration."""
        p_type = self.provider_type.lower()
        
        if p_type == "ollama":
            self.provider = OllamaProvider(
                base_url=self.config.get("base_url", "http://localhost:11434"),
                model=self.config.get("model")
            )
        elif p_type == "openai":
            api_key = self.security.get_api_key("openai")
            self.provider = OpenAICompatibleProvider(
                base_url="https://api.openai.com/v1",
                api_key=api_key,
                model=self.config.get("model")
            )
        elif p_type == "gemini":
            api_key = self.security.get_api_key("gemini")
            self.provider = GeminiProvider(
                api_key=api_key,
                model=self.config.get("model")
            )
        elif p_type == "lm_studio":
            self.provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=self.config.get("model")
            )
        elif p_type == "llama_cpp":
            self.provider = OpenAICompatibleProvider(
                base_url="http://localhost:8080/v1",
                model=self.config.get("model")
            )
        elif p_type == "openai_compatible":
            api_key = self.security.get_api_key("custom_ai")
            self.provider = OpenAICompatibleProvider(
                base_url=self.config.get("base_url", ""),
                api_key=api_key,
                model=self.config.get("model")
            )
        else:
            print(f"[LLM] Unknown provider type: {p_type}")

    def update_config(self, provider_type: str, config: Dict):
        """Update service configuration and re-initialize."""
        self.provider_type = provider_type
        self.config = config or {}
        self._initialize_provider()

    def is_available(self) -> bool:
        return self.provider is not None and self.provider.is_available()

    def get_available_models(self) -> List[str]:
        if self.provider:
            return self.provider.get_available_models()
        return []

    def set_model(self, model: str) -> bool:
        if self.provider:
            return self.provider.set_model(model)
        return False

    @property
    def model(self) -> Optional[str]:
        if self.provider:
            return self.provider.get_current_model()
        return None

    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Unified method for text generation."""
        if self.provider:
            return self.provider.generate_response(prompt, timeout)
        return None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Unified method for generating embeddings with local fallback."""
        if not texts:
            return []
            
        embeddings = []
        if self.provider and self.provider_type.lower() != "gemini":
            try:
                embeddings = self.provider.generate_embeddings(texts)
            except Exception as e:
                print(f"[LLMService] Provider embedding error: {e}")
        
        # Fallback if primary provider failed or is not available
        if not embeddings:
            if not hasattr(self, '_local_embeddings'):
                self._local_embeddings = LocalEmbeddingProvider()
            embeddings = self._local_embeddings.generate_embeddings(texts)
            
        return embeddings

    def preload_model(self, model_name: str = None) -> bool:
        if self.provider:
            return self.provider.preload_model(model_name)
        return False

# Backwards compatibility wrapper
class OllamaClient:
    """Legacy wrapper for LLMService to maintain compatibility with existing code."""
    def __init__(self, base_url: str = "http://localhost:11434", model: Optional[str] = None) -> None:
        self._service = LLMService(provider_type="ollama", config={"base_url": base_url, "model": model})
    
    def is_available(self) -> bool: 
        return self._service.is_available()
    
    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]: 
        return self._service.generate_response(prompt, timeout)
    
    def get_available_models(self) -> List[str]: 
        return self._service.get_available_models()
    
    def set_model(self, model: str) -> bool: 
        return self._service.set_model(model)
    
    def preload_model(self, model_name: Optional[str] = None) -> bool: 
        return self._service.preload_model(model_name)
    
    @property
    def model(self) -> Optional[str]: 
        return self._service.model

class LLMThreadedQuery:
    """Helper for async queries (formerly OllamaThreadedQuery)."""
    def __init__(self, service: LLMService) -> None:
        self.service = service
        self.result: Optional[str] = None
        self.error: Optional[str] = None

    def _worker(self, method_name: str, args: tuple, callback) -> None:
        try:
            method = getattr(self.service, method_name)
            self.result = method(*args)
            callback(self.result)
        except Exception as e:
            self.error = str(e)
            callback(None)

    def generate_async(self, prompt: str, callback, timeout: int = 60) -> None:
        threading.Thread(target=self._worker, args=("generate_response", (prompt, timeout), callback), daemon=True).start()

# Helper for compatibility
OllamaThreadedQuery = LLMThreadedQuery

# Global service instance
_ai_service: Optional[LLMService] = None

def get_ai_client(provider_type: Optional[str] = None, config: Optional[Dict] = None) -> LLMService:
    """Get or create the unified AI service instance."""
    global _ai_service
    if _ai_service is None:
        # Initial call, use defaults if not provided
        p = provider_type or "ollama"
        c = config or {}
        _ai_service = LLMService(p, c)
    elif provider_type is not None:
        # Update call - only update if a provider_type is explicitly passed
        _ai_service.update_config(provider_type, config)
    return _ai_service

def is_ai_available() -> bool:
    """Check if the configured AI service is available."""
    client = get_ai_client()
    return client.is_available()

# --- BACKWARD COMPATIBILITY ALIASES (Deprecated) ---

def get_llm_client(provider_type: str = "ollama", config: Optional[Dict] = None) -> LLMService:
    return get_ai_client(provider_type, config)

def get_ollama_client(base_url: str = "http://localhost:11434", model: Optional[str] = None) -> LLMService:
    """Legacy wrapper for get_ai_client."""
    return get_ai_client("ollama", {"base_url": base_url, "model": model})

def is_ollama_available() -> bool:
    """Legacy wrapper for is_ai_available."""
    return is_ai_available()
