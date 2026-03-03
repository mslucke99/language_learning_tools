import requests
import json
import time
from typing import List, Optional, Dict
from src.services.llm_providers.base import LLMProvider

class OllamaProvider(LLMProvider):
    """Provider implementation for local Ollama LLM."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = None):
        self.base_url = base_url
        self.available = False
        self.available_models = []
        self.model = model
        self._check_connection()
        
        # If model not specified, try to pick first available
        if not self.model and self.available_models:
            self.model = self.available_models[0]

    def _check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [m["name"] for m in data.get("models", [])]
                self.available = len(self.available_models) > 0
                return True
        except Exception as e:
            self.available = False
        return False

    def is_available(self) -> bool:
        return self._check_connection()

    def get_available_models(self) -> List[str]:
        self._check_connection()
        return self.available_models

    def set_model(self, model_name: str) -> bool:
        if model_name in self.available_models:
            self.model = model_name
            return True
        return False

    def get_current_model(self) -> Optional[str]:
        return self.model

    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        if not self.available or not self.model:
            return None
            
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "keep_alive": "5m"
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
        except:
            pass
        return None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Implementation for Ollama embedding endpoint."""
        if not self.available or not self.model:
            return []
            
        try:
            # Modern Ollama /api/embed supports multiple inputs
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": texts
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embeddings", [])
        except Exception as e:
            print(f"[Ollama] Embedding Error: {e}")
            
        return []

    def preload_model(self, model_name: str = None) -> bool:
        target_model = model_name or self.model
        if not target_model:
            return False
            
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": target_model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": -1 
                },
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
