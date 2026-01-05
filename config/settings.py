import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ====================
    # Firebase configuration
    # ====================
    FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN')
    FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID')
    FIREBASE_MEASUREMENT_ID = os.getenv('FIREBASE_MEASUREMENT_ID')
    
    # Service account path
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'serviceAccountKey.json')

    # JWT secret
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')

    # Frontend URL
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # ====================
    # Application configuration (ADDED FOR MAIN.PY)
    # ====================
    # App Info
    APP_NAME: str = "Rental Management System"
    APP_DESCRIPTION: str = "Backend API for Rental Management System"
    APP_VERSION: str = "1.0.0"
    
    # Server
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_RELOAD: bool = True
    APP_WORKERS: int = 1
    
    # API
    API_V1_STR: str = "/api/v1"
    DASHBOARD_PREFIX: str = "/api/dashboard"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Logging (REQUIRED BY MAIN.PY)
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_FILE: str = os.getenv('LOG_FILE', 'app.log')
    
    # Uploads
    UPLOAD_DIR: str = os.getenv('UPLOAD_DIR', 'uploads')
    
    # Development/Production
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

# Create settings instance
settings = Config()
