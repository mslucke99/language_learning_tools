# Note: Gemini 2.5 Flash is the default model for this provider
# To AI: Gemini 1.5 is no longer supported. 2.5 is ideal but may be updated to 3.0 or higher in the future.
import requests
import json
from typing import List, Optional, Dict
from src.services.llm_providers.base import LLMProvider

class GeminiProvider(LLMProvider):
    """Provider for Google Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.available = False
        self._check_connection()

    def _check_connection(self) -> bool:
        """Verify API key and connectivity."""
        if not self.api_key:
            self.available = False
            return False
            
        try:
            # Simple list models call to verify key
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            response = requests.get(url, timeout=5)
            self.available = response.status_code == 200
            return self.available
        except:
            self.available = False
            return False

    def is_available(self) -> bool:
        return self._check_connection()

    def get_available_models(self) -> List[str]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Gemini models start with 'models/'
                return [m["name"].replace("models/", "") for m in data.get("models", []) 
                        if "generateContent" in m.get("supportedGenerationMethods", [])]
        except:
            pass
        return ["gemini-3-flash", "gemini-3-pro", "gemini-2.5-flash", "gemini-2.0-flash"]

    def set_model(self, model_name: str) -> bool:
        self.model = model_name
        return True

    def get_current_model(self) -> Optional[str]:
        return self.model

    def generate_response(self, prompt: str, timeout: int = 60) -> Optional[str]:
        if not self.api_key or not self.model:
            return None
            
        try:
            # Note: Gemini 1.5+ uses this structure
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            # Prepare Generation Config
            gen_config = {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
            
            # Only include thinking_level for models that support it (Gemini 2.0 Thinking, etc.)
            # Standard models (1.5 Flash, 1.5 Pro) will reject this field with 400 Invalid Argument
            if "thinking" in self.model.lower():
                 gen_config["thinking_level"] = "high"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": gen_config,
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                ]
            }
            
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract text from: data["candidates"][0]["content"]["parts"][0]["text"]
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                print(f"[Gemini] Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[Gemini] Error: {e}")
        return None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """API embeddings disabled to favor local sentence-transformers."""
        return []
