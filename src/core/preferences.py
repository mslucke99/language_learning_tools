from typing import Optional
from src.core.database import FlashcardDatabase

class UserPreferences:
    """Encapsulates user-specific preferences stored in the database."""
    
    def __init__(self, db: FlashcardDatabase):
        self.db = db
        
    def get(self, key: str, default: str = "") -> str:
        """Get a preference value from the database."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT setting_value FROM study_settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default
        
    def set(self, key: str, value: str):
        """Set a preference value in the database."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO study_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, str(value))
        )
        self.db.conn.commit()

    # Convenience properties for common preferences
    @property
    def native_language(self) -> str:
        return self.get("native_language", "English")
    
    @native_language.setter
    def native_language(self, value: str):
        self.set("native_language", value)

    @property
    def study_language(self) -> str:
        return self.get("study_language", "Spanish")
        
    @study_language.setter
    def study_language(self, value: str):
        self.set("study_language", value)
        
    @property
    def ui_language(self) -> str:
        return self.get("ui_language", "en")
        
    @ui_language.setter
    def ui_language(self, value: str):
        self.set("ui_language", value)
