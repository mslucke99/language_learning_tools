import os
from typing import Optional
from pathlib import Path
from .base import STTProvider
from src.services.audio_service import STTResult

class WhisperLocalProvider(STTProvider):
    """
    Uses faster-whisper for local, offline transcription.
    Requires downloading a model on first use.
    """
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        
    def is_available(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False

    def _load_model(self):
        if not self._model:
            from faster_whisper import WhisperModel
            import torch
            
            # Determine if CUDA is available for faster transcription
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            try:
                self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            except Exception as e:
                print(f"[Whisper Local] Failed to load model: {e}")
                raise RuntimeError(f"Failed to load faster-whisper model: {e}")

    def transcribe(self, audio_path: Path) -> STTResult:
        if not self.is_available():
            raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
            
        self._load_model()
        
        segments, info = self._model.transcribe(str(audio_path), beam_size=5)
        
        text = " ".join([segment.text for segment in segments]).strip()
        # Information object contains language and language_probability
        return STTResult(
            text=text, 
            confidence=info.language_probability,
            language=info.language,
            duration=info.duration
        )
