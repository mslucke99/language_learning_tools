import json
import os
import locale
from typing import Dict, Optional

class LocalizationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
        self.locale_data: Dict[str, str] = {}
        self.current_locale = 'en'
        self.default_locale = 'en'
        self.locales_dir = os.path.join(os.path.dirname(__file__), '..', 'resources', 'locales')
        self.initialized = True
        self.load_locale(self.default_locale)

    def load_locale(self, lang_code: str):
        """Load a locale file. Falls back to default if failed."""
        try:
            path = os.path.join(self.locales_dir, f"{lang_code}.json")
            if not os.path.exists(path):
                # Try falling back to default if strictly different
                if lang_code != self.default_locale:
                    print(f"[Localization] Locale {lang_code} not found, falling back to {self.default_locale}")
                    self.load_locale(self.default_locale)
                    return
                else:
                    print(f"[Localization] Default locale {self.default_locale} not found at {path}!")
                    self.locale_data = {}
                    return
            
            with open(path, 'r', encoding='utf-8') as f:
                self.locale_data = json.load(f)
            self.current_locale = lang_code
            print(f"[Localization] Loaded locale: {lang_code}")
            
        except Exception as e:
            print(f"[Localization] Error loading locale {lang_code}: {e}")
            if lang_code != self.default_locale:
                self.load_locale(self.default_locale)

    def tr(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Translate a key. Falls back to default or key name if not found."""
        text = self.locale_data.get(key, default if default is not None else key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

# Global instance
_loc_manager = LocalizationManager()

def tr(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Helper function for quick translation."""
    return _loc_manager.tr(key, default, **kwargs)

def set_locale(lang_code: str):
    _loc_manager.load_locale(lang_code)

def get_current_locale() -> str:
    return _loc_manager.current_locale
