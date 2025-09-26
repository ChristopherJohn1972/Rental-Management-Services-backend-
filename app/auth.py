# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials, db
from pydantic import BaseModel
from typing import Optional, List
import datetime
import uuid

# Initialize Firebase
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://rental-management-system-d7106-default-rtdb.firebaseio.com/'
})

app = FastAPI()
security = HTTPBearer()

# Dependency to verify Firebase ID token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Pydantic models
class TenantProfile(BaseModel):
    full_name: str
    phone: str
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None

class MaintenanceRequest(BaseModel):
    title: str
    description: str
    category: str
    urgency: str = "medium"

class PaymentMethod(BaseModel):
    type: str  # "credit_card", "bank_account"
    details: dict  # Token from payment processor

# Routes
@app.get("/")
async def root():
    return {"message": "Rental Management System API"}

@app.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']
    ref = db.reference(f'/tenants/{user_id}')
    profile = ref.get()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.post("/profile")
async def update_profile(profile: TenantProfile, current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']
    ref = db.reference(f'/tenants/{user_id}/personal_info')
    ref.set(profile.dict())

    # Mark profile as complete
    user_ref = db.reference(f'/users/{user_id}/profile_complete')
    user_ref.set(True)

    return {"message": "Profile updated successfully"}

@app.post("/maintenance-requests")
async def create_maintenance_request(
    request: MaintenanceRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['uid']

    # Get user's unit ID
    tenant_ref = db.reference(f'/tenants/{user_id}/lease_info/unit_id')
    unit_id = tenant_ref.get()

    if not unit_id:
        raise HTTPException(status_code=400, detail="No assigned unit found")

    # Create maintenance request
    request_id = str(uuid.uuid4())
    request_data = {
        **request.dict(),
        "tenant_id": user_id,
        "unit_id": unit_id,
        "status": "submitted",
        "created_at": datetime.datetime.now().isoformat()
    }

    ref = db.reference(f'/maintenance_requests/{request_id}')
    ref.set(request_data)

    # Add to user's maintenance requests list
    user_requests_ref = db.reference(f'/tenants/{user_id}/maintenance_requests/{request_id}')
    user_requests_ref.set(True)

    return {"id": request_id, "message": "Maintenance request submitted successfully"}

@app.get("/maintenance-requests")
async def get_maintenance_requests(current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']

    # Get list of user's maintenance request IDs
    requests_ref = db.reference(f'/tenants/{user_id}/maintenance_requests')
    request_ids = requests_ref.get()

    if not request_ids:
        return []

    # Get details for each request
    requests = []
    for request_id in request_ids.keys():
        request_ref = db.reference(f'/maintenance_requests/{request_id}')
        request_data = request_ref.get()
        if request_data:
            requests.append({"id": request_id, **request_data})

    return requests

@app.get("/payments")
async def get_payment_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']

    # Query payments for this user
    ref = db.reference('/payments')
    payments = ref.order_by_child('tenant_id').equal_to(user_id).get()

    if not payments:
        return []

    return payments

@app.post("/fcm-token")
async def register_fcm_token(token: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']
    ref = db.reference(f'/users/{user_id}/fcm_tokens/{token}')
    ref.set(True)
    return {"message": "FCM token registered successfully"}

@app.delete("/fcm-token/{token}")
async def remove_fcm_token(token: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user['uid']
    ref = db.reference(f'/users/{user_id}/fcm_tokens/{token}')
    ref.delete()
    return {"message": "FCM token removed successfully"}
