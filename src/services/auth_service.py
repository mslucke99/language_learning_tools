import os
import json
import logging
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger("AuthService")

# Scopes required for Firebase Auth ID token generation or user info
# Note: To fully simulate Firebase Auth, we'd exchange this for a Firebase Token.
# For this "Admin SDK" implementation, we mostly need the user's EMAIL/ID to know WHERE to save data.
# We will use the 'openid', 'email', 'profile' scopes to get user identity.
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / "language_learning_tools"
USER_CREDENTIALS_FILE = CONFIG_DIR / "user_credentials.json"
CLIENT_SECRETS_FILE = CONFIG_DIR / "client_secrets.json" # User must download this from GCSE

class AuthService:
    def __init__(self):
        self._credentials = None
        self._user_info = None
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def get_user_info(self):
        if self._user_info:
            return self._user_info
        
        # If we have credentials, try to fetch info? 
        # For simplicity, we just return the cached info if available from login
        return self._user_info

    def sign_in(self):
        """
        Initiates the OAuth2 flow to log the user in.
        Returns the user info dict (email, sub/uid, name).
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens
        if USER_CREDENTIALS_FILE.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(USER_CREDENTIALS_FILE), SCOPES)
            except Exception as e:
                logger.error(f"Error loading saved creds: {e}")

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = self._start_new_flow()
            else:
                creds = self._start_new_flow()
            
            # Save the credentials for the next run
            with open(USER_CREDENTIALS_FILE, 'w') as token:
                token.write(creds.to_json())

        self._credentials = creds
        
        # Verify/Get User Info
        return self._fetch_user_profile(creds)

    def _start_new_flow(self):
        if not CLIENT_SECRETS_FILE.exists():
            raise FileNotFoundError(
                f"Client Secrets file not found at {CLIENT_SECRETS_FILE}.\n"
                "Please download 'OAuth 2.0 Client ID' JSON from Google Cloud Console "
                "and save it as 'client_secrets.json' in the config folder."
            )
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        return creds

    def _fetch_user_profile(self, creds):
        from googleapiclient.discovery import build
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        # user_info contains: id, email, verified_email, name, given_name, family_name, picture
        self._user_info = user_info
        logger.info(f"User logged in: {user_info.get('email')}")
        return user_info

    def get_current_user_id(self):
        """Returns the Google User ID (sub) if logged in, else None."""
        if self._user_info:
            return self._user_info.get('id')
        
        # Try to load from creds if not explicitly signed in this session but valid
        if USER_CREDENTIALS_FILE.exists() and not self._credentials:
             try:
                self.sign_in() # Auto-load
                if self._user_info:
                    return self._user_info.get('id')
             except Exception:
                 pass
        
        return None
