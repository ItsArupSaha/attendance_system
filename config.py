import os
from dotenv import load_dotenv
load_dotenv()

# Firebase Configuration
# Note: Firestore doesn't require FIREBASE_DATABASE_URL
# It uses the project_id from service account credentials

# Firebase Service Account Credentials (from environment variables)
FIREBASE_TYPE = os.getenv("FIREBASE_TYPE", "service_account")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_PRIVATE_KEY_ID = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n')  # Handle newlines in env var
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL", "")
FIREBASE_CLIENT_ID = os.getenv("FIREBASE_CLIENT_ID", "")
FIREBASE_AUTH_URI = os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
FIREBASE_TOKEN_URI = os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token")
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs")
FIREBASE_CLIENT_X509_CERT_URL = os.getenv("FIREBASE_CLIENT_X509_CERT_URL", "")

# Application Configuration
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", "15"))
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "8000"))
FLASK_DEBUG = bool(int(os.getenv("FLASK_DEBUG", "0")))


def get_firebase_credentials_dict():
    """
    Build Firebase credentials dictionary from environment variables.
    
    Returns:
        dict: Firebase service account credentials dictionary
    """
    return {
        "type": FIREBASE_TYPE,
        "project_id": FIREBASE_PROJECT_ID,
        "private_key_id": FIREBASE_PRIVATE_KEY_ID,
        "private_key": FIREBASE_PRIVATE_KEY,
        "client_email": FIREBASE_CLIENT_EMAIL,
        "client_id": FIREBASE_CLIENT_ID,
        "auth_uri": FIREBASE_AUTH_URI,
        "token_uri": FIREBASE_TOKEN_URI,
        "auth_provider_x509_cert_url": FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
        "client_x509_cert_url": FIREBASE_CLIENT_X509_CERT_URL
    }
