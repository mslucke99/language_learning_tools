import os
from typing import Optional
from pathlib import Path
from .base import STTProvider
from src.services.audio_service import STTResult
from src.services.llm_providers.security import KeyringManager

class WhisperCloudProvider(STTProvider):
    """
    Uses OpenAI or Groq Whisper API for transcription.
    """
    def __init__(self, base_url: str = "https://api.openai.com/v1", model: str = "whisper-1"):
        self.base_url = base_url
        self.model = model
        self.security = KeyringManager()
        
        # Determine which key to use based on URL
        if "groq.com" in self.base_url:
            self._api_key = self.security.get_api_key("groq")
        else:
            self._api_key = self.security.get_api_key("openai")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def transcribe(self, audio_path: Path) -> STTResult:
        if not self.is_available():
            raise RuntimeError("Whisper Cloud API key not configured")
            
        import requests
        
        url = f"{self.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self._api_key}"
        }
        
        with open(audio_path, "rb") as f:
            files = {
                "file": (audio_path.name, f, "audio/wav")
            }
            data = {
                "model": self.model
            }
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()
                return STTResult(text=text, confidence=1.0)
            else:
                print(f"[Whisper Cloud API] Error {response.status_code}: {response.text}")
                return STTResult(text="", confidence=0.0)
