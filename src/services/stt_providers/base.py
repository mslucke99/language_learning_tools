from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from src.services.audio_service import STTResult

class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is reachable and configured correctly."""
        pass
        
    @abstractmethod
    def transcribe(self, audio_path: Path) -> STTResult:
        """
        Transcribe an audio file and return the STTResult.
        Should raise an exception or return an empty/failed STTResult on error.
        """
        pass
