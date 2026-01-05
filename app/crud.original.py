# app/crud.py - CRUD operations
from typing import Optional, Dict, List
from datetime import datetime
from flask import current_app
from .firebase_init import db_ref
from .models import (
    User, Property, MaintenanceRequest, Payment,
    UserCreate, UserUpdate, PropertyCreate, 
    MaintenanceRequestCreate, PaymentCreate,
    UserResponse, PropertyResponse, 
    MaintenanceRequestResponse, PaymentResponse,
    UserRole, PropertyType, MaintenanceStatus,
    PaymentStatus, UrgencyLevel
)

class CRUDUser:
    def create(self, user_id: str, user_in: UserCreate) -> UserResponse:
        """Create a new user"""
        user_data = {
            'uid': user_id,
            'email': user_in.email,
            'first_name': user_in.first_name,
            'last_name': user_in.last_name,
            'phone': user_in.phone,
            'role': user_in.role.value if hasattr(user_in.role, 'value') else user_in.role,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add additional fields if provided
        if hasattr(user_in, 'apartment'):
            user_data['apartment'] = user_in.apartment
        if hasattr(user_in, 'house_number'):
            user_data['house_number'] = user_in.house_number
            
        User.create(user_data)
        
        # Return as UserResponse
        return UserResponse(**user_data)
    
    def get(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        user_data = User.get(user_id)
        if user_data:
            return UserResponse(**user_data)
        return None
    
    def update(self, user_id: str, user_in: UserUpdate) -> Optional[UserResponse]:
        """Update user"""
        updates = {}
        for field, value in user_in.dict(exclude_unset=True).items():
            if value is not None:
                if hasattr(value, 'value'):
                    updates[field] = value.value
                else:
                    updates[field] = value
        
        if updates:
            User.update(user_id, updates)
            return self.get(user_id)
        return None

class CRUDProperty:
    def create(self, property_in: PropertyCreate) -> PropertyResponse:
        """Create a new property"""
        property_data = property_in.dict()
        result = Property.create(property_data)
        return PropertyResponse(**result)
    
    def get_all(self) -> List[PropertyResponse]:
        """Get all properties"""
        properties = Property.get_all()
        if isinstance(properties, dict):
            return [PropertyResponse(**{**prop, 'id': pid}) for pid, prop in properties.items()]
        return []

class CRUDMaintenance:
    def create(self, user_id: str, request_in: MaintenanceRequestCreate) -> MaintenanceRequestResponse:
        """Create a maintenance request"""
        request_data = request_in.dict()
        request_data['user_id'] = user_id
        request_data['status'] = MaintenanceStatus.PENDING.value
        result = MaintenanceRequest.create(request_data)
        return MaintenanceRequestResponse(**result)
    
    def get_by_user(self, user_id: str) -> List[MaintenanceRequestResponse]:
        """Get maintenance requests by user"""
        requests = MaintenanceRequest.get_by_user(user_id)
        if isinstance(requests, dict):
            return [MaintenanceRequestResponse(**{**req, 'id': rid}) for rid, req in requests.items()]
        return []

class CRUDPayment:
    def create(self, user_id: str, payment_in: PaymentCreate) -> PaymentResponse:
        """Create a payment"""
        payment_data = payment_in.dict()
        payment_data['user_id'] = user_id
        payment_data['status'] = PaymentStatus.PENDING.value
        result = Payment.create(payment_data)
        return PaymentResponse(**result)
    
    def get_by_user(self, user_id: str) -> List[PaymentResponse]:
        """Get payments by user"""
        payments = Payment.get_by_user(user_id)
        if isinstance(payments, dict):
            return [PaymentResponse(**{**pay, 'id': pid}) for pid, pay in payments.items()]
        return []

# Create instances for easy import
user = CRUDUser()
property_crud = CRUDProperty()
maintenance = CRUDMaintenance()
payment = CRUDPayment()



# ========================
# SIMPLE CRUD FIX
# ========================

# Create a simple crud object using type()
crud = type('CRUD', (), {
    'user': user,
    'property': property_crud, 
    'maintenance': maintenance,
    'payment': payment
})()

# That's it! main.py can now import 'crud'
