# app/models.py
from enum import Enum
from datetime import datetime
from flask import current_app
from typing import Optional, Dict
# Make sure db_ref points to your Firebase Realtime Database reference
from app.firebase_config import db_ref  

# -----------------------------
# Enums
# -----------------------------
class UserRole(str, Enum):
    ADMIN = "admin"
    TENANT = "tenant"

# -----------------------------
# User Model
# -----------------------------
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

# -----------------------------
# Property Model
# -----------------------------
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

# -----------------------------
# MaintenanceRequest Model
# -----------------------------
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

# -----------------------------
# Payment Model
# -----------------------------
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
