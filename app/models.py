# app/models.py - WITH ALL ENUM VALUES
from enum import Enum
from datetime import datetime
from flask import current_app
from typing import Optional, Dict
from app.firebase_init import db_ref 

# ====================
# ENUMS
# ====================

class UserRole(str, Enum):
    ADMIN = "admin"
    TENANT = "tenant"

class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"

class UnitStatus(str, Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    UNDER_MAINTENANCE = "under_maintenance"
    RESERVED = "reserved"

class MaintenanceStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ====================
# PYDANTIC MODELS
# ====================
from pydantic import BaseModel, EmailStr
from typing import List

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.TENANT

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None

class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    type: PropertyType
    total_units: int
    year_built: Optional[int] = None
    amenities: List[str] = []

class MaintenanceRequestCreate(BaseModel):
    unit_id: str
    issue: str
    description: str
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM

class PaymentCreate(BaseModel):
    tenant_id: str
    amount: float
    payment_method: str
    reference: str

# ====================
# DATABASE MODELS (original code)
# ====================

class User:
    @staticmethod
    def create(user_data: Dict):
        try:
            user_ref = db_ref.child('users').child(user_data['uid'])
            user_ref.set({
                'email': user_data['email'],
                'name': user_data.get('name', ''),
                'role': user_data.get('role', UserRole.TENANT.value),
                'apartment': user_data.get('apartment', ''),
                'house_number': user_data.get('house_number', ''),
                'phone': user_data.get('phone', ''),
                'emergency_contact': user_data.get('emergency_contact', ''),
                'move_in_date': user_data.get('move_in_date', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            return user_data
        except Exception as e:
            current_app.logger.error(f"Error creating user: {e}")
            raise e

    @staticmethod
    def get(user_id: str):
        try:
            user = db_ref.child('users').child(user_id).get()
            return user
        except Exception as e:
            current_app.logger.error(f"Error getting user: {e}")
            return None

    @staticmethod
    def update(user_id: str, updates: Dict):
        try:
            updates['updated_at'] = datetime.now().isoformat()
            db_ref.child('users').child(user_id).update(updates)
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating user: {e}")
            return False

class Property:
    @staticmethod
    def create(property_data: Dict):
        try:
            property_id = db_ref.child('properties').push().key
            property_data['id'] = property_id
            property_data['created_at'] = datetime.now().isoformat()
            property_data['updated_at'] = datetime.now().isoformat()
            
            db_ref.child('properties').child(property_id).set(property_data)
            return property_data
        except Exception as e:
            current_app.logger.error(f"Error creating property: {e}")
            raise e

    @staticmethod
    def get_all():
        try:
            properties = db_ref.child('properties').get()
            return properties or {}
        except Exception as e:
            current_app.logger.error(f"Error getting properties: {e}")
            return {}

class MaintenanceRequest:
    @staticmethod
    def create(request_data: Dict):
        try:
            request_id = db_ref.child('maintenance_requests').push().key
            request_data['id'] = request_id
            request_data['created_at'] = datetime.now().isoformat()
            request_data['updated_at'] = datetime.now().isoformat()
            request_data['status'] = 'pending'
            
            db_ref.child('maintenance_requests').child(request_id).set(request_data)
            return request_data
        except Exception as e:
            current_app.logger.error(f"Error creating maintenance request: {e}")
            raise e

    @staticmethod
    def get_by_user(user_id: str):
        try:
            requests = db_ref.child('maintenance_requests').order_by_child('user_id').equal_to(user_id).get()
            return requests or {}
        except Exception as e:
            current_app.logger.error(f"Error getting user maintenance requests: {e}")
            return {}

class Payment:
    @staticmethod
    def create(payment_data: Dict):
        try:
            payment_id = db_ref.child('payments').push().key
            payment_data['id'] = payment_id
            payment_data['created_at'] = datetime.now().isoformat()
            payment_data['updated_at'] = datetime.now().isoformat()
            
            db_ref.child('payments').child(payment_id).set(payment_data)
            return payment_data
        except Exception as e:
            current_app.logger.error(f"Error creating payment: {e}")
            raise e

    @staticmethod
    def get_by_user(user_id: str):
        try:
            payments = db_ref.child('payments').order_by_child('user_id').equal_to(user_id).get()
            return payments or {}
        except Exception as e:
            current_app.logger.error(f"Error getting user payments: {e}")
            return {}
# Add these to your existing Pydantic Models section in models.py

class UserResponse(BaseModel):
    uid: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: UserRole
    apartment: Optional[str] = None
    house_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    move_in_date: Optional[str] = None
    created_at: str
    updated_at: str

class PropertyResponse(BaseModel):
    id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    type: PropertyType
    total_units: int
    year_built: Optional[int] = None
    amenities: List[str] = []
    created_at: str
    updated_at: str

class MaintenanceRequestResponse(BaseModel):
    id: str
    unit_id: str
    user_id: Optional[str] = None
    issue: str
    description: str
    urgency: UrgencyLevel
    status: MaintenanceStatus
    created_at: str
    updated_at: str
    assigned_to: Optional[str] = None
    completed_at: Optional[str] = None

class PaymentResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    amount: float
    payment_method: str
    reference: str
    status: PaymentStatus
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: str
    updated_at: str

# You might also need these for the crud operations
class UserList(BaseModel):
    users: List[UserResponse]

class PropertyList(BaseModel):
    properties: List[PropertyResponse]
