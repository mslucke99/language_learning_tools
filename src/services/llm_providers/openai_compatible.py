import requests
import json
from typing import List, Optional, Dict
from src.services.llm_providers.base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI and other OpenAI-compatible APIs 
    (LM Studio, llama.cpp, vLLM, Groq, etc.)
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.available = False
        self._check_connection()

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _check_connection(self) -> bool:
        """Verify endpoint availability."""
        try:
            # Most compatible backends support /v1/models
            response = requests.get(
                f"{self.base_url}/models", 
                headers=self._get_headers(),
                timeout=5
            )
            self.available = response.status_code == 200
            return self.available
        except:
            self.available = False
            return False

    def is_available(self) -> bool:
        return self._check_connection()

    def get_available_models(self) -> List[str]:
        """Fetch list of models from the compatible endpoint."""
        try:
            response = requests.get(
                f"{self.base_url}/models", 
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                # Unified format is data["data"] -> items with "id"
                if isinstance(data, dict) and "data" in data:
                    return [m["id"] for m in data["data"]]
        except:
            pass
        return []

    def set_model(self, model_name: str) -> bool:
        self.model = model_name
        return True

    def get_current_model(self) -> Optional[str]:
        return self.model

    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        if not self.model:
            return None
            
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"[LLM] Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[LLM] Error: {e}")
        return None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Implementation for OpenAI-compatible embedding endpoint."""
        if not self.model:
            # Fallback to a common embedding model if none is specified for embeddings
            model = "text-embedding-3-small"
        else:
            model = self.model
            
        try:
            payload = {
                "model": model,
                "input": texts
            }
            
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Unified format: data["data"] -> items with "embedding"
                return [item["embedding"] for item in data["data"]]
            else:
                print(f"[LLM] Embedding Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[LLM] Embedding Error: {e}")
        return []
