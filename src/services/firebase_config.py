import os
import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

# Configuration Paths
CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / "language_learning_tools"
SERVICE_ACCOUNT_KEY_FILE = CONFIG_DIR / "firebase_service_account.json"

# Logger
logger = logging.getLogger("FirebaseConfig")

def initialize_firebase():
    """
    Initialize the Firebase Admin SDK.
    Requires 'firebase_service_account.json' to be present in the config dir.
    """
    if not SERVICE_ACCOUNT_KEY_FILE.exists():
        logger.error(f"Firebase Service Account key not found at: {SERVICE_ACCOUNT_KEY_FILE}")
        return None

    try:
        # Check if already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(SERVICE_ACCOUNT_KEY_FILE))
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
        
        return firestore.client()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None

def get_firestore_client():
    """Wrapper to get the client, initializing if necessary."""
    try:
        return firestore.client()
    except ValueError:
        # Not initialized yet
        return initialize_firebase()
