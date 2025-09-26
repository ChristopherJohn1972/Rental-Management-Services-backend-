import firebase_admin
from firebase_admin import credentials, firestore, auth, db
import pyrebase
from config import Config
import json

class FirebaseService:
    _initialized = False
    
    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
                # Initialize Firebase Admin SDK
                cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT_PATH)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': Config.FIREBASE_DATABASE_URL
                })
                
                # Initialize Pyrebase for client-side operations
                cls.pyrebase_config = {
                    "apiKey": Config.FIREBASE_API_KEY,
                    "authDomain": Config.FIREBASE_AUTH_DOMAIN,
                    "databaseURL": Config.FIREBASE_DATABASE_URL,
                    "projectId": Config.FIREBASE_PROJECT_ID,
                    "storageBucket": Config.FIREBASE_STORAGE_BUCKET,
                    "messagingSenderId": Config.FIREBASE_MESSAGING_SENDER_ID,
                    "appId": Config.FIREBASE_APP_ID,
                    "measurementId": Config.FIREBASE_MEASUREMENT_ID
                }
                
                cls.firebase = pyrebase.initialize_app(cls.pyrebase_config)
                cls._initialized = True
                print("Firebase initialized successfully")
                
            except Exception as e:
                print(f"Error initializing Firebase: {str(e)}")
                raise
    
    @classmethod
    def get_firestore(cls):
        if not cls._initialized:
            cls.initialize()
        return firestore.client()
    
    @classmethod
    def get_auth(cls):
        if not cls._initialized:
            cls.initialize()
        return auth
    
    @classmethod
    def get_realtime_db(cls):
        if not cls._initialized:
            cls.initialize()
        return db
    
    @classmethod
    def get_pyrebase_auth(cls):
        if not cls._initialized:
            cls.initialize()
        return cls.firebase.auth()
