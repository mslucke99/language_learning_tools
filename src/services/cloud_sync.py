"""
Cloud Sync Manager - Google Drive integration for cross-device sync.

Security Model:
- credentials.json (App ID/Secret): Stored in ~/.config/language_learning_suite/
- User tokens: Stored via keyring (Windows Credential Manager / macOS Keychain)
"""

import os
import json
from pathlib import Path

# Keyring is optional - fall back to file-based storage if unavailable
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    print("[CloudSync] Warning: keyring not available, tokens will be stored in a local file.")
from datetime import datetime
from typing import Optional, Tuple

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Only access files created by this app
SERVICE_NAME = 'LanguageLearningSuite'
CONFIG_DIR = Path.home() / '.config' / 'language_learning_suite'
CREDENTIALS_FILE = CONFIG_DIR / 'credentials.json'
TOKEN_FILE = CONFIG_DIR / 'token.json'  # Fallback token storage
DRIVE_FOLDER_NAME = 'LanguageLearningSuite'
KEYRING_SERVICE = 'language_learning_suite'
KEYRING_USERNAME = 'google_oauth_token'


class CloudSyncManager:
    """Manages Google Drive sync operations."""
    
    def __init__(self, db_path: str):
        """
        Initialize the Cloud Sync Manager.
        
        Args:
            db_path: Path to the local flashcards.db file.
        """
        self.db_path = db_path
        self.creds: Optional[Credentials] = None
        self.service = None
        self.folder_id: Optional[str] = None
        
        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
    @staticmethod
    def is_available() -> bool:
        """Check if Google API libraries are installed."""
        return GOOGLE_API_AVAILABLE
    
    def has_credentials_file(self) -> bool:
        """Check if the app credentials file exists."""
        return CREDENTIALS_FILE.exists()
    
    def is_authenticated(self) -> bool:
        """Check if we have valid user credentials."""
        return self.creds is not None and self.creds.valid
    
    def _load_token_from_keyring(self) -> Optional[str]:
        """Load the OAuth token from keyring or fallback file."""
        if KEYRING_AVAILABLE:
            try:
                token = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
                if token:
                    return token
            except Exception:
                pass
        
        # Fallback to file
        if TOKEN_FILE.exists():
            try:
                return TOKEN_FILE.read_text()
            except Exception:
                pass
        return None
    
    def _save_token_to_keyring(self, token_json: str):
        """Save the OAuth token to keyring or fallback file."""
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token_json)
                return
            except Exception as e:
                print(f"[CloudSync] Warning: Could not save token to keyring: {e}")
        
        # Fallback to file
        try:
            TOKEN_FILE.write_text(token_json)
        except Exception as e:
            print(f"[CloudSync] Warning: Could not save token to file: {e}")
    
    def _delete_token_from_keyring(self):
        """Remove the OAuth token from keyring and fallback file."""
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                pass
        
        # Also delete file if exists
        if TOKEN_FILE.exists():
            try:
                TOKEN_FILE.unlink()
            except Exception:
                pass
    
    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with Google Drive.
        
        Returns:
            (success, message) tuple
        """
        if not GOOGLE_API_AVAILABLE:
            return False, "Google API libraries not installed. Run: pip install -r requirements.txt"
        
        if not self.has_credentials_file():
            return False, f"Missing credentials.json. Place it in: {CREDENTIALS_FILE}"
        
        # Try to load existing token from keyring
        token_json = self._load_token_from_keyring()
        if token_json:
            try:
                token_data = json.loads(token_json)
                self.creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception:
                self.creds = None
        
        # Refresh or get new credentials
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
            except Exception:
                self.creds = None
        
        if not self.creds or not self.creds.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            except Exception as e:
                return False, f"Authentication failed: {e}"
        
        # Save token to keyring
        self._save_token_to_keyring(self.creds.to_json())
        
        # Build the Drive service
        try:
            self.service = build('drive', 'v3', credentials=self.creds)
            return True, "Successfully connected to Google Drive!"
        except Exception as e:
            return False, f"Failed to connect to Drive service: {e}"
    
    def disconnect(self):
        """Disconnect and clear stored credentials."""
        self._delete_token_from_keyring()
        self.creds = None
        self.service = None
        self.folder_id = None
    
    def _get_or_create_folder(self) -> Optional[str]:
        """Get or create the app's folder in Drive."""
        if self.folder_id:
            return self.folder_id
        
        if not self.service:
            return None
        
        # Search for existing folder
        query = f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            self.folder_id = files[0]['id']
            return self.folder_id
        
        # Create folder
        file_metadata = {
            'name': DRIVE_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        self.folder_id = folder.get('id')
        return self.folder_id
    
    def backup_to_cloud(self) -> Tuple[bool, str]:
        """
        Upload the local database to Google Drive.
        
        Returns:
            (success, message) tuple
        """
        if not self.is_authenticated():
            return False, "Not authenticated. Please connect first."
        
        if not os.path.exists(self.db_path):
            return False, f"Database not found: {self.db_path}"
        
        folder_id = self._get_or_create_folder()
        if not folder_id:
            return False, "Could not access Drive folder."
        
        # Check if file already exists
        filename = os.path.basename(self.db_path)
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        existing_files = results.get('files', [])
        
        media = MediaFileUpload(self.db_path, mimetype='application/x-sqlite3')
        
        try:
            if existing_files:
                # Update existing file
                file_id = existing_files[0]['id']
                self.service.files().update(fileId=file_id, media_body=media).execute()
            else:
                # Create new file
                file_metadata = {'name': filename, 'parents': [folder_id]}
                self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True, f"Backup complete at {timestamp}"
        except Exception as e:
            return False, f"Backup failed: {e}"
    
    def restore_from_cloud(self) -> Tuple[bool, str]:
        """
        Download the database from Google Drive, replacing local copy.
        
        Returns:
            (success, message) tuple
        """
        if not self.is_authenticated():
            return False, "Not authenticated. Please connect first."
        
        folder_id = self._get_or_create_folder()
        if not folder_id:
            return False, "Could not access Drive folder."
        
        filename = os.path.basename(self.db_path)
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])
        
        if not files:
            return False, "No backup found in cloud."
        
        file_id = files[0]['id']
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            # Create backup of current local file
            if os.path.exists(self.db_path):
                backup_path = self.db_path + '.backup'
                os.replace(self.db_path, backup_path)
            
            with open(self.db_path, 'wb') as f:
                import io
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True, f"Restore complete at {timestamp}. Local backup saved as .backup"
        except Exception as e:
            return False, f"Restore failed: {e}"
    
    def merge_and_restore(self, parent_window=None) -> Tuple[bool, str]:
        """
        Download the database from Google Drive and MERGE with local copy.
        Uses conflict resolution for rows modified on both sides.
        
        Args:
            parent_window: Tkinter parent for conflict dialogs (optional).
        
        Returns:
            (success, message) tuple
        """
        from src.services.sync_merger import SyncMerger, ConflictInfo, ConflictResolution
        from src.services.conflict_dialog import show_conflict_dialog
        from src.core.database import FlashcardDatabase
        import tempfile
        import shutil
        
        if not self.is_authenticated():
            return False, "Not authenticated. Please connect first."
        
        folder_id = self._get_or_create_folder()
        if not folder_id:
            return False, "Could not access Drive folder."
        
        filename = os.path.basename(self.db_path)
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])
        
        if not files:
            return False, "No backup found in cloud."
        
        file_id = files[0]['id']
        
        try:
            # Download to temp file
            temp_dir = tempfile.mkdtemp()
            temp_db_path = os.path.join(temp_dir, 'remote_flashcards.db')
            
            request = self.service.files().get_media(fileId=file_id)
            with open(temp_db_path, 'wb') as f:
                import io
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            # Get last sync time from local DB
            db = FlashcardDatabase(self.db_path)
            sync_meta = db.get_sync_metadata()
            last_sync = sync_meta.get('last_pc_sync')
            db.close()
            
            # Create merger
            merger = SyncMerger(self.db_path, temp_db_path, last_sync)
            
            # Set conflict handler if we have a parent window
            if parent_window:
                def on_conflict(conflict: ConflictInfo) -> ConflictResolution:
                    return show_conflict_dialog(parent_window, conflict)
                merger.on_conflict = on_conflict
            
            # Perform merge
            stats = merger.merge_all()
            merger.close()
            
            # Update sync metadata
            db = FlashcardDatabase(self.db_path)
            db.update_sync_metadata(pc_sync=True)
            db.close()
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            # Build summary
            total_added = sum(s[0] for s in stats.values())
            total_updated = sum(s[1] for s in stats.values())
            total_conflicts = sum(s[2] for s in stats.values())
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True, f"Merge complete at {timestamp}. Added: {total_added}, Updated: {total_updated}, Conflicts: {total_conflicts}"
        
        except Exception as e:
            return False, f"Merge failed: {e}"
