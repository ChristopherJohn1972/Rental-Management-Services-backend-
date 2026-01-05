import os
import logging
import firebase_admin
from firebase_admin import credentials, auth, db, storage

# Configure logging
logger = logging.getLogger(__name__)

# Firebase configuration from environment variables
FIREBASE_TYPE = os.environ.get('FIREBASE_TYPE')
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
FIREBASE_AUTH_URI = os.environ.get('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
FIREBASE_TOKEN_URI = os.environ.get('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token')
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = os.environ.get('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs')
FIREBASE_CLIENT_X509_CERT_URL = os.environ.get('FIREBASE_CLIENT_X509_CERT_URL')
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL')
FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')

# Firebase app instance
firebase_app = None
db_ref = None
storage_bucket = None
auth_client = None

# Initialize Firebase if credentials are available
if all([FIREBASE_TYPE, FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL, FIREBASE_CLIENT_ID]):
    try:
        cred = credentials.Certificate({
            'type': FIREBASE_TYPE,
            'project_id': FIREBASE_PROJECT_ID,
            'private_key_id': FIREBASE_PRIVATE_KEY_ID,
            'private_key': FIREBASE_PRIVATE_KEY,
            'client_email': FIREBASE_CLIENT_EMAIL,
            'client_id': FIREBASE_CLIENT_ID,
            'auth_uri': FIREBASE_AUTH_URI,
            'token_uri': FIREBASE_TOKEN_URI,
            'auth_provider_x509_cert_url': FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
            'client_x509_cert_url': FIREBASE_CLIENT_X509_CERT_URL
        })
        
        firebase_config = {'databaseURL': FIREBASE_DATABASE_URL} if FIREBASE_DATABASE_URL else {}
        
        firebase_app = firebase_admin.initialize_app(cred, firebase_config)
        logger.info("Firebase initialized successfully")
        
        # Get database reference
        if FIREBASE_DATABASE_URL:
            db_ref = db.reference()
        else:
            db_ref = None
            logger.warning("No Firebase database URL configured")
        
        # Get storage bucket (with error handling)
        try:
            if FIREBASE_STORAGE_BUCKET:
                storage_bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
            else:
                storage_bucket = None
                logger.warning("No Firebase storage bucket configured")
        except Exception as e:
            logger.warning(f"Could not initialize Firebase storage: {e}")
            storage_bucket = None
        
        # Get auth client
        auth_client = auth
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        db_ref = None
        storage_bucket = None
        auth_client = None
else:
    logger.warning("Firebase credentials not found in environment variables")
    logger.info("Running in mock mode - Firebase features will be limited")
