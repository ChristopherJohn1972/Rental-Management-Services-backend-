# app/main.py
import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

import firebase_admin
from firebase_admin import credentials, auth, db, storage

from config.settings import Config
settings = Config()  # optional, if your code uses 'settings'
from app.auth import get_current_user, verify_token
from app.crud import crud
from app.models import (
    UserRole, MaintenanceRequestCreate, MaintenanceRequestUpdate,
    PaymentCreate, PropertyCreate, UnitCreate, LeaseInfo, NotificationCreate
)

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

# Firebase initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
    # Initialize Firebase
    cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': settings.FIREBASE_DATABASE_URL,
        'storageBucket': settings.FIREBASE_STORAGE_BUCKET
    })
    logger.info("Firebase initialized successfully")

    # Create upload directory if it doesn't exist
    os.makedirs(getattr(settings, "UPLOAD_DIR", "uploads"), exist_ok=True)
    logger.info(f"Upload directory created: {getattr(settings, 'UPLOAD_DIR', 'uploads')}")

except Exception as e:
    logger.error(f"Error during startup: {str(e)}")
    raise

logger.info("Startup complete. Backend is ready to run.")

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
# ROOT & HEALTH ENDPOINTS
# ========================

@app.get("/")
async def root():
    return {
        "message": "Rental Management System API",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2023-01-01T00:00:00Z"}

@app.get("/api/v1/info")
async def api_info():
    return {
        "api_version": "v1",
        "endpoints": {
            "dashboard": f"{settings.API_V1_STR}/dashboard",
            "auth": f"{settings.API_V1_STR}/auth",
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
# AUTHENTICATION ENDPOINTS
# ========================

from pydantic import BaseModel
from datetime import datetime, timedelta

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

@app.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    User login endpoint
    """
    try:
        # Verify user credentials with Firebase Auth
        user = auth.get_user_by_email(login_data.email)
        
        # In a real implementation, you'd verify the password properly
        # This is a simplified example - you should use Firebase Auth REST API
        # or verify the password properly
        
        # Create a custom token or use your JWT implementation
        custom_token = auth.create_custom_token(user.uid)
        
        return TokenResponse(
            access_token=custom_token.decode('utf-8'),
            token_type="bearer",
            expires_in=3600  # 1 hour
        )
    except auth.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/register")
async def register(login_data: LoginRequest):
    """
    User registration endpoint
    """
    try:
        # Create new user in Firebase Auth
        user = auth.create_user(
            email=login_data.email,
            password=login_data.password
        )
        
        return {
            "message": "User created successfully",
            "user_id": user.uid,
            "email": user.email
        }
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

# Simple redirect for root to login (optional)
@app.get("/login")
async def login_page():
    """
    Redirect to login or return login info
    """
    return {
        "message": "Please use POST /login with email and password for authentication",
        "example_request": {
            "email": "user@example.com",
            "password": "your_password"
        }
    }

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
            # Tenants can only see their own requests
            requests = await crud.get_maintenance_requests(
                tenant_id=current_user['uid'],
                status=status
            )
        elif current_user.get('role') in [UserRole.STAFF, UserRole.ADMIN]:
            # Staff and admin can see all requests
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
            payments = await crud.get_payments()  # All payments for staff/admin
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
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        workers=settings.APP_WORKERS
    )