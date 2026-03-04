import os
from typing import Optional
from pathlib import Path
from .base import STTProvider
from src.services.audio_service import STTResult
from src.services.llm_providers.gemini_provider import GeminiProvider
from src.services.llm_providers.security import KeyringManager

class GeminiSTTProvider(STTProvider):
    """
    Uses Gemini Multimodal to transcribe audio files.
    """
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.security = KeyringManager()
        self._api_key = self.security.get_api_key("gemini")
        # Reuse existing GeminiProvider implementation where possible
        self._gemini = GeminiProvider(api_key=self._api_key, model=self.model)

    def is_available(self) -> bool:
        return bool(self._api_key) and self._gemini.is_available()

    def transcribe(self, audio_path: Path) -> STTResult:
        """
        Transcribe the audio using the Gemini API directly.
        Since Gemini allows multimodal data (text + audio), we just ask it to transcribe.
        """
        if not self.is_available():
            raise RuntimeError("Gemini STT not configured or unavailable")
            
        import requests
        import base64
        import json
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
            
        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self._api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Please accurately transcribe the following speech. Provide only the transcription, no markdown formatting or extra commentary."},
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": b64_audio
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temp for accurate transcription
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            try:
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                # Gemini doesn't easily provide confidence directly for this API without more complex parsing
                # but we can assume high confidence for now.
                return STTResult(text=text, confidence=1.0)
            except (KeyError, IndexError):
                print(f"[Gemini STT] Failed to parse response: {result}")
                return STTResult(text="", confidence=0.0)
        else:
            print(f"[Gemini STT] API error {response.status_code}: {response.text}")
            return STTResult(text="", confidence=0.0)
