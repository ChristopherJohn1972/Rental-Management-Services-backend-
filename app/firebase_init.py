# app/firebase_init.py
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db as firebase_db, auth as firebase_auth, storage

logger = logging.getLogger(__name__)

def _load_credential():
    """Load service account from FIREBASE_CREDENTIALS env (JSON string) or local file."""
    cred_env = os.environ.get("FIREBASE_CREDENTIALS")
    if cred_env:
        try:
            return credentials.Certificate(json.loads(cred_env))
        except Exception as e:
            logger.exception("Invalid FIREBASE_CREDENTIALS env var: %s", e)
            raise
    if os.path.exists("serviceAccountKey.json"):
        return credentials.Certificate("serviceAccountKey.json")
    return None

FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL")  # e.g. https://<project-id>.firebaseio.com
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET")  # e.g. <project-id>.appspot.com

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
            # Attempt app-default initialization (works on GCP hosts). If it fails, we still continue but db_ref will be None.
            try:
                firebase_admin.initialize_app(options=init_opts or None)
                logger.warning("Firebase initialized without explicit credentials (application default).")
            except Exception as e:
                logger.warning("Firebase could not be initialized (no credentials): %s", e)
    except Exception as e:
        logger.exception("Failed to initialize Firebase: %s", e)

# Expose safe references (could be None if init failed)
if firebase_admin._apps:
    try:
        db_ref = firebase_db.reference("/")
    except Exception as e:
        logger.exception("Failed to get Realtime DB reference: %s", e)
        db_ref = None

    try:
        storage_bucket = storage.bucket() if FIREBASE_STORAGE_BUCKET else None
    except Exception as e:
        logger.exception("Failed to get storage bucket object: %s", e)
        storage_bucket = None
else:
    db_ref = None
    storage_bucket = None

# Also export firebase_auth
# (Even if auth operations fail until firebase_admin is initialized, this is convenient)
try:
    auth_client = firebase_auth
except Exception:
    auth_client = None
