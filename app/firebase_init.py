import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db as firebase_db, auth as firebase_auth, storage

logger = logging.getLogger(__name__)

def _load_credential():
    """Load service account from FIREBASE_CREDENTIALS_PATH env or local file."""
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if cred_path and os.path.exists(cred_path):
        try:
            return credentials.Certificate(cred_path)
        except Exception as e:
            logger.exception("Failed to load credential from path %s: %s", cred_path, e)
            raise
    # fallback to local file
    if os.path.exists("serviceAccountKey.json"):
        return credentials.Certificate("serviceAccountKey.json")
    return None

# Correct environment variable names from Render
FIREBASE_DB_URL = os.environ.get("FIREBASE_DATABASE_URL")
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET")

_cred = _load_credential()

# Initialize Firebase only once
if not firebase_admin._apps:
    try:
        init_opts = {}
        if FIREBASE_DB_URL:
            init_opts["databaseURL"] = FIREBASE_DB_URL
        if FIREBASE_STORAGE_BUCKET:
            init_opts["storageBucket"] = FIREBASE_STORAGE_BUCKET

        if _cred:
            firebase_admin.initialize_app(_cred, init_opts or None)
            logger.info("Firebase initialized with provided credentials")
        else:
            try:
                firebase_admin.initialize_app(options=init_opts or None)
                logger.warning("Firebase initialized without explicit credentials (application default).")
            except Exception as e:
                logger.warning("Firebase could not be initialized (no credentials): %s", e)
    except Exception as e:
        logger.exception("Failed to initialize Firebase: %s", e)

# Expose safe references
if firebase_admin._apps:
    try:
        db_ref = firebase_db.reference("/")
    except Exception as e:
        logger.exception("Failed to get Realtime DB reference: %s", e)
        db_ref = None

    try:
try:
    if FIREBASE_STORAGE_BUCKET:
        storage_bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
    else:
        storage_bucket = None
        print("Warning: No Firebase storage bucket configured")
except Exception as e:
    print(f"Warning: Could not initialize Firebase storage: {e}")
    storage_bucket = None
    except Exception as e:
        logger.exception("Failed to get storage bucket object: %s", e)
        storage_bucket = None
else:
    db_ref = None
    storage_bucket = None

# Export auth
auth_client = firebase_auth
