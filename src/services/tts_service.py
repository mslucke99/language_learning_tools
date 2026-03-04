import os
from tempfile import gettempdir
from pathlib import Path
from abc import ABC, abstractmethod
import hashlib

# Will try importing libraries when needed to avoid blowing up on startup
# if not installed

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, language: str) -> Path:
        """Generate audio for text and return path to the saved file."""
        pass
        
    @abstractmethod
    def play(self, audio_path: Path):
        """Play the audio file."""
        pass


class TTSService:
    """Manages text-to-speech generation and playback with caching."""
    def __init__(self, provider_type: str = "gtts"):
        self._provider_type = provider_type
        self._cache_dir = Path(gettempdir()) / "language_learning_tts_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._provider = self._get_provider(provider_type)
        
    def _get_provider(self, p_type: str) -> TTSProvider:
        if p_type == "pyttsx3":
            return Pyttsx3Provider()
        return GTTSProvider()  # Default

    def update_config(self, provider_type: str):
        if self._provider_type != provider_type:
            self._provider_type = provider_type
            self._provider = self._get_provider(provider_type)

    def _get_cache_path(self, text: str, language: str) -> Path:
        """Generate a deterministic path for a given text and language."""
        hash_input = f"{language}:{text}".encode('utf-8')
        file_hash = hashlib.md5(hash_input).hexdigest()
        return self._cache_dir / f"{file_hash}.mp3"

    def play_text(self, text: str, language: str = "en"):
        """Generate (or fetch from cache) and play the audio."""
        if not text.strip():
            return
            
        # pyttsx3 plays directly, bypassing file caching
        if self._provider_type == "pyttsx3":
            self._provider.synthesize(text, language)
            return

        cache_path = self._get_cache_path(text, language)
        if not cache_path.exists():
            generated_path = self._provider.synthesize(text, language)
            if generated_path:
                try:
                    import shutil
                    shutil.move(str(generated_path), str(cache_path))
                except Exception as e:
                    print(f"[TTS] Failed to cache file: {e}")
                    cache_path = generated_path # Fallback

        if cache_path.exists():
            self._provider.play(cache_path)


class GTTSProvider(TTSProvider):
    def synthesize(self, text: str, language: str) -> Path:
        from gtts import gTTS
        # Map our study_language to gTTS lang codes
        # Assuming language might be full name like "Spanish" or code like "es"
        lang_map = {
            "spanish": "es", "french": "fr", "german": "de", "japanese": "ja",
            "korean": "ko", "chinese": "zh-cn", "english": "en", "italian": "it"
        }
        lang_code = lang_map.get(language.lower(), language.lower()[:2])
        
        try:
            tts = gTTS(text=text, lang=lang_code)
            temp_path = Path(gettempdir()) / "temp_gtts.mp3"
            tts.save(str(temp_path))
            return temp_path
        except Exception as e:
            print(f"[gTTS] Generation failed: {e}")
            return None

    def play(self, audio_path: Path):
        try:
            import playsound
            # Playsound has well-known threading/blocking issues on some OSes
            playsound.playsound(str(audio_path))
        except Exception as e:
            print(f"[gTTS] Playback failed: {e}")
            # Fallback for windows if playsound fails
            if os.name == 'nt':
                os.system(f"start /min mplay32 /play /close {audio_path}")
            # Fallback for macOS
            elif os.uname().sysname == 'Darwin':
                os.system(f"afplay {audio_path}")


class Pyttsx3Provider(TTSProvider):
    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
        except Exception as e:
            print(f"[Pyttsx3] Init failed: {e}")
            self.engine = None

    def synthesize(self, text: str, language: str) -> Path:
        """Pyttsx3 plays directly and blocks, so we skip file gen for simple use cases."""
        if not self.engine:
            return None
        self.engine.say(text)
        self.engine.runAndWait()
        return None
        
    def play(self, audio_path: Path):
        # We don't save files in Pyttsx3 for the simple use case
        pass
