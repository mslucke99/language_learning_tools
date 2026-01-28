import os
import base64
from typing import Optional

# Optional dependencies
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

class KeyringManager:
    """Manages secure storage of API keys."""
    
    SERVICE_NAME = "LanguageLearningSuite"
    
    def __init__(self):
        self._fallback_key = self._get_or_create_fallback_key()

    def _get_or_create_fallback_key(self) -> Optional[bytes]:
        """Generate a machine-specific key for Fernet fallback."""
        if not HAS_CRYPTOGRAPHY:
            return None
            
        # Use machine name + user name as a seed for the key
        # This is not perfectly secure but better than plain text for a fallback
        import platform
        import getpass
        seed = f"{platform.node()}-{getpass.getuser()}".encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'static_salt_for_language_suite', # In a real app, use a unique salt
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(seed))

    def set_api_key(self, provider: str, api_key: str):
        """Store an API key securely."""
        if HAS_KEYRING:
            try:
                keyring.set_password(self.SERVICE_NAME, provider, api_key)
                return True
            except:
                pass
                
        # Fallback to local encrypted file if keyring fails or missing
        if HAS_CRYPTOGRAPHY and self._fallback_key:
            try:
                f = Fernet(self._fallback_key)
                encrypted = f.encrypt(api_key.encode()).decode()
                
                # Store in a hidden-ish file in app data or config
                # For now, let's just use the current directory or a .secrets file
                # The implementation plan mentioned a .secrets file
                with open(".secrets", "a") as secrets_file:
                    secrets_file.write(f"{provider}:{encrypted}\n")
                return True
            except:
                pass
        return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve a stored API key."""
        if HAS_KEYRING:
            try:
                key = keyring.get_password(self.SERVICE_NAME, provider)
                if key:
                    return key
            except:
                pass
                
        # Fallback check
        if HAS_CRYPTOGRAPHY and self._fallback_key and os.path.exists(".secrets"):
            try:
                f = Fernet(self._fallback_key)
                with open(".secrets", "r") as secrets_file:
                    for line in secrets_file:
                        if line.startswith(f"{provider}:"):
                            encrypted = line.split(":", 1)[1].strip()
                            return f.decrypt(encrypted.encode()).decode()
            except:
                pass
        return None

    def delete_api_key(self, provider: str):
        """Remove a stored API key."""
        if HAS_KEYRING:
            try:
                keyring.delete_password(self.SERVICE_NAME, provider)
            except:
                pass
        
        if os.path.exists(".secrets"):
            try:
                lines = []
                with open(".secrets", "r") as secrets_file:
                    lines = secrets_file.readlines()
                
                with open(".secrets", "w") as secrets_file:
                    for line in lines:
                        if not line.startswith(f"{provider}:"):
                            secrets_file.write(line)
            except:
                pass
