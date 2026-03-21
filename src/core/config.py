import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

@dataclass
class AppConfig:
    """Central configuration for the Language Learning Suite."""
    
    # AI / LLM Settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "120"))
    preload_on_startup: bool = os.getenv("PRELOAD_ON_STARTUP", "true").lower() == "true"
    
    # Embedding settings
    embedding_speed: str = os.getenv("EMBEDDING_SPEED", "slow")  # 'off', 'slow', 'fast'
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # UI Features
    enable_dynamic_styling: bool = os.getenv("ENABLE_DYNAMIC_STYLING", "true").lower() == "true"
    
    # UI & Localization (Fallback defaults)
    ui_language: str = os.getenv("UI_LANGUAGE", "en")
    native_language: str = os.getenv("NATIVE_LANGUAGE", "English")
    study_language: str = os.getenv("STUDY_LANGUAGE", "Spanish")
    
    # Audio / Voice Settings
    stt_provider: str = os.getenv("STT_PROVIDER", "gemini")
    tts_provider: str = os.getenv("TTS_PROVIDER", "gtts")
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "44100"))
    
    # Paths
    db_path: str = os.getenv("DB_PATH", "flashcards.db")
    config_path: str = os.getenv("CONFIG_PATH", "config.json")
    
    def save_to_file(self, path: Optional[str] = None):
        """Save non-sensitive configuration to a JSON file."""
        target_path = path or self.config_path
        
        # Exclude sensitive keys if we ever add them here
        # For now, all these are non-sensitive as API keys are in Keyring
        config_data = asdict(self)
        
        # Remove paths and internal state before saving
        keys_to_exclude = ["db_path", "config_path"]
        for key in keys_to_exclude:
            config_data.pop(key, None)
            
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config to {target_path}: {e}")

    @classmethod
    def load_from_file(cls, path: str = "config.json") -> "AppConfig":
        """Load configuration from JSON and environment variables."""
        config = cls()
        
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    
                # Update config with file data, but let ENV VARS take precedence
                # (Environment variables were already loaded into class defaults or explicitly set)
                for key, value in file_data.items():
                    # Only override if NOT set by ENV VAR (primitive check)
                    env_key = key.upper()
                    if os.getenv(env_key) is None and hasattr(config, key):
                        setattr(config, key, value)
            except Exception as e:
                print(f"[Config] Error loading config from {path}: {e}")
                
        return config

# Global config instance
config = AppConfig.load_from_file()
