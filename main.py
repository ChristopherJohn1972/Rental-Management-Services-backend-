import os
import logging
import json
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr

import firebase_admin
from firebase_admin import credentials, auth, db, apps
import requests  # For Firebase REST API

from config.settings import Config
from app.auth import get_current_user
from app.crud import crud
from app.models import (
    UserRole, MaintenanceRequestCreate, MaintenanceRequestUpdate,
    PaymentCreate, PropertyCreate, UnitCreate, LeaseInfo, NotificationCreate
)

# Initialize settings
settings = Config()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for authentication
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user_id: str
    email: str
    role: str

class UserProfile(BaseModel):
    uid: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: str
    created_at: str

# Firebase initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Validate that all required environment variables are set
            required_env_vars = [
                "FIREBASE_TYPE", "FIREBASE_PROJECT_ID", "FIREBASE_PRIVATE_KEY_ID",
                "FIREBASE_PRIVATE_KEY", "FIREBASE_CLIENT_EMAIL", "FIREBASE_CLIENT_ID",
                "FIREBASE_DATABASE_URL", "FIREBASE_STORAGE_BUCKET"
            ]

            missing_vars = [var for var in required_env_vars if not os.getenv(var)]
            if missing_vars:
                logger.warning(f"Missing Firebase environment variables: {', '.join(missing_vars)}")
                logger.info("Using mock authentication and database mode")
            else:
                # Use environment variables for Firebase credentials
                firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
                
                if not firebase_private_key.startswith("-----BEGIN PRIVATE KEY-----"):
                    logger.warning("Invalid Firebase private key format")
                    logger.info("Using mock authentication and database mode")
                else:
                    cred = credentials.Certificate({
                        "type": os.getenv("FIREBASE_TYPE"),
                        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                        "private_key": firebase_private_key,
                        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                        "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                        "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
                    })

                    firebase_config = {
                        'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
                    }

                    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
                    if storage_bucket:
                        firebase_config['storageBucket'] = storage_bucket

                    firebase_admin.initialize_app(cred, firebase_config)
                    logger.info("Firebase initialized successfully")
        else:
            logger.info("Firebase already initialized - using existing instance")

        # Create upload directory if it doesn't exist
        upload_dir = getattr(settings, "UPLOAD_DIR", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        logger.info(f"Upload directory ready: {upload_dir}")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        logger.info("Application starting with limited functionality")

    logger.info("Startup complete")
    yield
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Security
security = HTTPBearer()

# ========================
# AUTHENTICATION ENDPOINTS
# ========================

@app.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user and return Firebase ID token
    """
    try:
        # Use Firebase REST API to authenticate
        api_key = os.getenv("FIREBASE_WEB_API_KEY")
        if not api_key:
            logger.warning("FIREBASE_WEB_API_KEY not set, using mock authentication")
            # Mock response for development
            return TokenResponse(
                access_token="mock_jwt_token",
                token_type="bearer",
                expires_in=3600,
                refresh_token="mock_refresh_token",
                user_id="mock_user_id",
                email=login_data.email,
                role=UserRole.TENANT
            )
        
        # Sign in with email and password using Firebase REST API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": login_data.email,
            "password": login_data.password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code != 200:
            error_msg = result.get('error', {}).get('message', 'Login failed')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        
        # Get user details from Firebase Auth
        firebase_user = auth.get_user(result['localId'])
        
        # Get user role from database
        user_ref = db.reference(f'users/{firebase_user.uid}')
        user_data = user_ref.get() or {}
        user_role = user_data.get('role', UserRole.TENANT)
        
        return TokenResponse(
            access_token=result['idToken'],
            token_type="bearer",
            expires_in=int(result['expiresIn']),
            refresh_token=result['refreshToken'],
            user_id=firebase_user.uid,
            email=firebase_user.email,
            role=user_role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@app.post("/register", response_model=TokenResponse)
async def register(register_data: RegisterRequest):
    """
    Register a new user
    """
    try:
        api_key = os.getenv("FIREBASE_WEB_API_KEY")
        if not api_key:
            logger.warning("FIREBASE_WEB_API_KEY not set, using mock registration")
            # Mock response for development
            return TokenResponse(
                access_token="mock_jwt_token",
                token_type="bearer",
                expires_in=3600,
                refresh_token="mock_refresh_token",
                user_id="mock_user_id",
                email=register_data.email,
                role=UserRole.TENANT
            )
        
        # Create user with Firebase REST API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
        payload = {
            "email": register_data.email,
            "password": register_data.password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        if response.status_code != 200:
            error_msg = result.get('error', {}).get('message', 'Registration failed')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Create user profile in database
        user_ref = db.reference(f'users/{result["localId"]}')
        user_data = {
            'email': register_data.email,
            'first_name': register_data.first_name,
            'last_name': register_data.last_name,
            'phone': register_data.phone,
            'role': UserRole.TENANT,
            'created_at': firebase_admin.db.SERVER_TIMESTAMP
        }
        user_ref.set(user_data)
        
        return TokenResponse(
            access_token=result['idToken'],
            token_type="bearer",
            expires_in=int(result['expiresIn']),
            refresh_token=result['refreshToken'],
            user_id=result['localId'],
            email=register_data.email,
            role=UserRole.TENANT
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.get("/login")
async def login_get():
    """
    Provide login page information
    """
    return {
        "message": "Please use POST /login with email and password for authentication",
        "required_fields": {
            "email": "string",
            "password": "string"
        }
    }

@app.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile
    """
    try:
        user_ref = db.reference(f'users/{current_user["uid"]}')
        user_data = user_ref.get() or {}
        
        return UserProfile(
            uid=current_user["uid"],
            email=user_data.get("email", current_user.get("email", "")),
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            phone=user_data.get("phone"),
            role=user_data.get("role", UserRole.TENANT),
            created_at=user_data.get("created_at", "")
        )
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile"
        )

# ========================
# ROOT & HEALTH ENDPOINTS
# ========================

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": "2023-01-01T00:00:00Z",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/api/v1/info")
async def api_info():
    return {
        "api_version": "v1",
        "service": settings.APP_NAME,
        "endpoints": {
            "auth": {
                "login": "POST /login",
                "register": "POST /register",
                "profile": "GET /profile"
            },
            "dashboard": {
                "user": f"{settings.DASHBOARD_PREFIX}/user",
                "staff": f"{settings.DASHBOARD_PREFIX}/staff", 
                "admin": f"{settings.DASHBOARD_PREFIX}/admin"
            },
            "properties": f"{settings.API_V1_STR}/properties",
            "maintenance": f"{settings.API_V1_STR}/maintenance",
            "payments": f"{settings.API_V1_STR}/payments",
            "tenants": f"{settings.API_V1_STR}/tenants"
        }
    }

# ========================
# DASHBOARD ENDPOINTS
# ========================

@app.get(f"{settings.DASHBOARD_PREFIX}/user", response_model=Dict[str, Any])
async def get_user_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get user dashboard data (for tenants)
    """
    if current_user.get('role') != UserRole.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Tenant role required."
        )

    try:
        dashboard_data = await crud.get_user_dashboard(
            current_user['uid'],
            current_user['role']
        )
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching user dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading user dashboard"
        )

@app.get(f"{settings.DASHBOARD_PREFIX}/staff", response_model=Dict[str, Any])
async def get_staff_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get staff dashboard data
    """
    if current_user.get('role') != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Staff role required."
        )

    try:
        dashboard_data = await crud.get_staff_dashboard(current_user['uid'])
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching staff dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading staff dashboard"
        )

@app.get(f"{settings.DASHBOARD_PREFIX}/admin", response_model=Dict[str, Any])
async def get_admin_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get admin dashboard data
    """
    if current_user.get('role') != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )

    try:
        dashboard_data = await crud.get_admin_dashboard()
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching admin dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading admin dashboard"
        )

# ========================
# MAINTENANCE ENDPOINTS
# ========================

@app.post(f"{settings.API_V1_STR}/maintenance/requests", response_model=Dict[str, Any])
async def create_maintenance_request(
    request: MaintenanceRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new maintenance request (Tenant only)
    """
    if current_user.get('role') != UserRole.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenants can create maintenance requests"
        )

    try:
        # Get user's unit ID from lease info
        tenant_ref = db.reference(f'tenants/{current_user["uid"]}/lease_info/unit_id')
        unit_id = tenant_ref.get()

        if not unit_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No unit assigned to your account"
            )

        result = await crud.create_maintenance_request(request, current_user['uid'], unit_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating maintenance request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating maintenance request"
        )

@app.get(f"{settings.API_V1_STR}/maintenance/requests", response_model=List[Dict[str, Any]])
async def get_maintenance_requests(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get maintenance requests with optional filtering
    """
    try:
        if current_user.get('role') == UserRole.TENANT:
            requests = await crud.get_maintenance_requests(
                tenant_id=current_user['uid'],
                status=status
            )
        elif current_user.get('role') in [UserRole.STAFF, UserRole.ADMIN]:
            requests = await crud.get_maintenance_requests(status=status)
        else:
            raise HTTPException(status_code=403, detail="Access denied")

        return requests
    except Exception as e:
        logger.error(f"Error fetching maintenance requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching maintenance requests"
        )

# ========================
# PROPERTY ENDPOINTS
# ========================

@app.get(f"{settings.API_V1_STR}/properties", response_model=List[Dict[str, Any]])
async def get_properties(
    search: Optional[str] = None,
    city: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get properties with optional search and filtering
    """
    try:
        filters = {}
        if city:
            filters['city'] = city

        properties = await crud.get_properties(filters, search)
        return properties
    except Exception as e:
        logger.error(f"Error fetching properties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching properties"
        )

@app.post(f"{settings.API_V1_STR}/properties", response_model=Dict[str, Any])
async def create_property(
    property_data: PropertyCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new property (Admin only)
    """
    if current_user.get('role') != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )

    try:
        property_obj = await crud.create_property(property_data)
        return property_obj.dict()
    except Exception as e:
        logger.error(f"Error creating property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating property"
        )

# ========================
# PAYMENT ENDPOINTS
# ========================

@app.get(f"{settings.API_V1_STR}/payments", response_model=List[Dict[str, Any]])
async def get_payments(current_user: dict = Depends(get_current_user)):
    """
    Get payment history for the current user
    """
    try:
        if current_user.get('role') == UserRole.TENANT:
            payments = await crud.get_payments(tenant_id=current_user['uid'])
        elif current_user.get('role') in [UserRole.STAFF, UserRole.ADMIN]:
            payments = await crud.get_payments()
        else:
            raise HTTPException(status_code=403, detail="Access denied")

        return payments
    except Exception as e:
        logger.error(f"Error fetching payments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payments"
        )

# ========================
# TENANT MANAGEMENT ENDPOINTS
# ========================

@app.get(f"{settings.API_V1_STR}/tenants", response_model=List[Dict[str, Any]])
async def get_tenants(
    property_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get tenants with optional filtering (Staff/Admin only)
    """
    if current_user.get('role') not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Staff or Admin role required."
        )

    try:
        tenants = await crud.get_tenants(property_id, unit_id)
        return tenants
    except Exception as e:
        logger.error(f"Error fetching tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching tenants"
        )

# ========================
# ERROR HANDLERS
# ========================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# ========================
# MAIN ENTRY POINT
# ========================

if __name__ == "__main__":	
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        workers=settings.APP_WORKERS
    )