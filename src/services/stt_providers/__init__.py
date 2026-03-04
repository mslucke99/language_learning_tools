from .base import STTProvider
from .gemini_stt import GeminiSTTProvider
from .whisper_cloud import WhisperCloudProvider
from .whisper_local import WhisperLocalProvider

def get_stt_provider(provider_name: str, **kwargs) -> STTProvider:
    """Factory method for getting STT providers."""
    p_name = provider_name.lower()
    
    if p_name == "gemini":
        return GeminiSTTProvider(**kwargs)
    elif p_name == "whisper_cloud":
        return WhisperCloudProvider(**kwargs)
    elif p_name == "whisper_local":
        return WhisperLocalProvider(**kwargs)
    else:
        # Default to Gemini if unknown
        print(f"Unknown STT provider '{provider_name}', falling back to gemini")
        return GeminiSTTProvider(**kwargs)
