"""
Dropbox Sync Manager for Language Learning Suite.
Handles authentication (PKCE) and file sync using Dropbox API for 'App Folder'.
"""

import os
import shutil
import json
import webbrowser
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import AuthError, ApiError

# --- CONFIGURATION ---
APP_KEY = "ax4jmmkstls02hc"  # Provided by User for LanguageLearningSuite-User app
# No explicit redirect URI needed for NoRedirect flow (users copy code)

CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / "language_learning_tools"
DROPBOX_TOKEN_FILE = CONFIG_DIR / "dropbox_token.json"
DB_PATH = Path("flashcards.db")

# Setup logger
logger = logging.getLogger("DropboxSync")
logger.setLevel(logging.INFO)

class DropboxSyncManager:
    """
    Manages Dropbox authentication and sync for the 'flashcards.db'.
    Uses 'App Folder' access, so files are at root '/' (e.g., /flashcards.db).
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.client: Optional[dropbox.Dropbox] = None
        self._auth_flow: Optional[DropboxOAuth2FlowNoRedirect] = None
        
        # Ensure config dir
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Attempt load
        self._load_token()

    def is_authenticated(self) -> bool:
        """Check if we have a valid client handle."""
        return self.client is not None

    def get_auth_url(self) -> str:
        """
        Start PKCE flow and return the URL the user needs to visit.
        """
        self._auth_flow = DropboxOAuth2FlowNoRedirect(
            APP_KEY,
            use_pkce=True,
            token_access_type='offline'  # Request refresh token
        )
        return self._auth_flow.start()

    def finish_auth(self, auth_code: str) -> Tuple[bool, str]:
        """
        Exchange the code the user pasted for an access/refresh token.
        """
        if not self._auth_flow:
            return False, "Auth flow not started. Call get_auth_url() first."
        
        try:
            oauth_result = self._auth_flow.finish(auth_code.strip())
            
            # Save tokens
            self._save_token(oauth_result.access_token, oauth_result.refresh_token, oauth_result.expires_at)
            
            # Initialize client
            self.client = dropbox.Dropbox(
                oauth2_access_token=oauth_result.access_token,
                oauth2_refresh_token=oauth_result.refresh_token,
                app_key=APP_KEY
            )
            
            # Verify
            account = self.client.users_get_current_account()
            return True, f"Connected as {account.name.display_name}"
            
        except Exception as e:
            logger.error(f"Auth failed: {e}")
            return False, str(e)

    def disconnect(self):
        """Remove local tokens."""
        self.client = None
        if DROPBOX_TOKEN_FILE.exists():
            try:
                DROPBOX_TOKEN_FILE.unlink()
            except Exception:
                pass

    def upload_db(self, message_callback: Callable[[str], None] = None) -> Tuple[bool, str]:
        """
        Upload local flashcards.db to Dropbox (overwrite).
        """
        if not self.client:
            return False, "Not authenticated."
        
        if not self.db_path.exists():
            return False, "Local database not found."

        try:
            if message_callback: message_callback("Reading local file...")
            with open(self.db_path, "rb") as f:
                data = f.read()
            
            if message_callback: message_callback("Uploading to Dropbox...")
            # mode=WriteMode.overwrite
            self.client.files_upload(
                data, 
                "/flashcards.db", 
                mode=dropbox.files.WriteMode.overwrite,
                mute=True
            )
            
            return True, "Upload successful."
            
        except ApiError as e:
            logger.error(f"Upload failed: {e}")
            return False, f"Dropbox API Error: {e}"
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False, str(e)

    def download_db_to_temp(self) -> Tuple[bool, Optional[str], str]:
        """
        Download remote flashcards.db to a temporary file.
        Returns: (success, temp_path, message)
        """
        if not self.client:
            return False, None, "Not authenticated."

        temp_path = self.db_path.parent / "temp_cloud_flashcards.db"
        
        try:
            # Check metadata first? No, just try download.
            metadata, result = self.client.files_download("/flashcards.db")
            
            with open(temp_path, "wb") as f:
                f.write(result.content)
            
            return True, str(temp_path), "Download successful."
            
        except ApiError as e:
            if isinstance(e.error, dropbox.files.DownloadError) and e.error.is_path() and e.error.get_path().is_not_found():
                return False, None, "No backup found in cloud."
            return False, None, f"Dropbox API Error: {e}"
        except Exception as e:
            return False, None, str(e)

    def create_checkpoint(self, local: bool = True, cloud: bool = False) -> Tuple[bool, str]:
        """
        Create a timestamped snapshot of the current DB locally and/or in the cloud.
        """
        if not self.db_path.exists():
            return False, "Database file not found."

        timestamp = datetime.now().strftime("%Y%mm%dd_%H%M%S")
        success_msgs = []

        try:
            # Local Checkpoint
            if local:
                backup_dir = CONFIG_DIR / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                local_path = backup_dir / f"flashcards_{timestamp}.db"
                shutil.copy2(self.db_path, local_path)
                success_msgs.append(f"Local: {local_path.name}")

            # Cloud Checkpoint
            if cloud:
                if not self.client:
                    return False, "Not authenticated for cloud checkpoint."
                
                with open(self.db_path, "rb") as f:
                    data = f.read()
                
                cloud_path = f"/checkpoints/flashcards_{timestamp}.db"
                self.client.files_upload(
                    data, 
                    cloud_path, 
                    mode=dropbox.files.WriteMode.add,
                    mute=True
                )
                success_msgs.append(f"Cloud: {cloud_path}")

            return True, "Checkpoints created: " + ", ".join(success_msgs)
        except Exception as e:
            logger.error(f"Checkpoint failed: {e}")
            return False, f"Checkpoint failed: {str(e)}"

    def _save_token(self, access_token, refresh_token, expires_at):
        """Save tokens to JSON config file (Keyring preferred in prod, using file for simplicity/consistency)."""
        data = {
            "oauth2_access_token": access_token,
            "oauth2_refresh_token": refresh_token,
            "oauth2_access_token_expiration": str(expires_at) if expires_at else None
        }
        try:
            with open(DROPBOX_TOKEN_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def _load_token(self):
        """Load tokens and initialize client if valid."""
        if not DROPBOX_TOKEN_FILE.exists():
            return
            
        try:
            with open(DROPBOX_TOKEN_FILE, 'r') as f:
                data = json.load(f)
            
            refresh_token = data.get("oauth2_refresh_token")
            # If we have a refresh token, we can perform token refresh automatically by the SDK
            if refresh_token:
                self.client = dropbox.Dropbox(
                    oauth2_refresh_token=refresh_token,
                    app_key=APP_KEY
                )
                # Test connection (optional, catches revoked tokens)
                try:
                    self.client.users_get_current_account()
                except AuthError:
                    print("Dropbox Token invalid/revoked.")
                    self.client = None
                    
        except Exception as e:
            logger.error(f"Failed to load token: {e}")

# Global instance
dropbox_manager = DropboxSyncManager()
