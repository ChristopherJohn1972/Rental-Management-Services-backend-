#firebase_config.py (Python Backend - Flask)
from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore, exceptions
import os
from functools import wraps
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import datetime
import re

# Import authentication functions from auth.py
from .auth import requires_role, validate_password, send_otp_email

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# Initialize Firebase
try:
    # For production, use environment variable or service account key
    if os.path.exists('serviceAccountKey.json'):
        firebase_cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(firebase_cred)
        print("Firebase initialized successfully")
    else:
        # Create a mock service account for development
        service_account_info = {
            "type": "service_account",
            "project_id": "rental-management-dev",
            "private_key_id": "mock-private-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk@rental-management-dev.iam.gserviceaccount.com",
            "client_id": "mock-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40rental-management-dev.iam.gserviceaccount.com"
        }
        firebase_cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(firebase_cred)
        print("Firebase initialized with mock credentials for development")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    print("Using mock authentication and database")

# Initialize Firestore
try:
    db = firestore.client()
except:
    db = None
    print("Using mock database for development")

# Configuration
app.config['SECRET_KEY'] = 'rental-management-secret-key-2023'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)

# Email configuration (for OTP)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-app-password')

# Mock data for demo (in production, use Firestore)
mock_users = {
    "admin@example.com": {
        "password": "Admin@123",
        "firstName": "Admin",
        "lastName": "User",
        "role": "admin",
        "uid": "admin-uid-123",
        "emailVerified": True
    },
    "staff@example.com": {
        "password": "Staff@123",
        "firstName": "Staff",
        "lastName": "Member",
        "role": "staff",
        "uid": "staff-uid-456",
        "emailVerified": True
    },
    "tenant@example.com": {
        "password": "Tenant@123",
        "firstName": "Tenant",
        "lastName": "User",
        "role": "tenant",
        "uid": "tenant-uid-789",
        "emailVerified": True
    }
}

# Mock properties data
mock_properties = [
    {
        "id": 1,
        "name": "Sunset Apartments",
        "address": "123 Sunset Blvd, Los Angeles, CA",
        "units": 12,
        "occupied": 8,
        "status": "Active",
        "type": "Apartment",
        "yearBuilt": 2010,
        "amenities": ["Pool", "Gym", "Parking"]
    },
    {
        "id": 2,
        "name": "Ocean View Villa",
        "address": "456 Ocean Drive, Miami, FL",
        "units": 6,
        "occupied": 4,
        "status": "Active",
        "type": "Villa",
        "yearBuilt": 2015,
        "amenities": ["Beach Access", "Pool", "Garden"]
    },
    {
        "id": 3,
        "name": "Downtown Lofts",
        "address": "789 Main St, New York, NY",
        "units": 8,
        "occupied": 5,
        "status": "Active",
        "type": "Loft",
        "yearBuilt": 2008,
        "amenities": ["Rooftop", "Concierge", "Parking"]
    },
    {
        "id": 4,
        "name": "Mountain Retreat",
        "address": "101 Mountain Rd, Denver, CO",
        "units": 4,
        "occupied": 0,
        "status": "Vacant",
        "type": "Cabin",
        "yearBuilt": 2020,
        "amenities": ["Fireplace", "Hot Tub", "Hiking Trails"]
    }
]

# Mock maintenance requests
mock_maintenance = [
    {
        "id": 101,
        "property": "Sunset Apartments - Unit 4B",
        "propertyId": 1,
        "unit": "4B",
        "issue": "Leaking faucet",
        "description": "Kitchen faucet has been leaking for 2 days",
        "reportedBy": "John Doe",
        "reportedById": "tenant-uid-789",
        "date": "2023-10-15",
        "status": "Pending",
        "priority": "Medium",
        "assignedTo": None
    },
    {
        "id": 102,
        "property": "Ocean View Villa - Unit 2",
        "propertyId": 2,
        "unit": "2",
        "issue": "Broken window",
        "description": "Living room window cracked after storm",
        "reportedBy": "Jane Smith",
        "reportedById": "user-456",
        "date": "2023-10-14",
        "status": "In Progress",
        "priority": "High",
        "assignedTo": "Mike Johnson"
    },
    {
        "id": 103,
        "property": "Downtown Lofts - Unit 5",
        "propertyId": 3,
        "unit": "5",
        "issue": "Electrical issue",
        "description": "Power outlet in bedroom not working",
        "reportedBy": "Mike Johnson",
        "reportedById": "staff-uid-456",
        "date": "2023-10-13",
        "status": "Resolved",
        "priority": "Medium",
        "assignedTo": "Electrician Services"
    },
    {
        "id": 104,
        "property": "Mountain Retreat - Unit 1",
        "propertyId": 4,
        "unit": "1",
        "issue": "Heating problem",
        "description": "Heating system not working properly",
        "reportedBy": "Sarah Wilson",
        "reportedById": "user-789",
        "date": "2023-10-12",
        "status": "Pending",
        "priority": "High",
        "assignedTo": None
    }
]

# Mock leases data
mock_leases = [
    {
        "id": 1001,
        "property": "Sunset Apartments",
        "propertyId": 1,
        "unit": "4B",
        "tenant": "John Doe",
        "tenantId": "tenant-uid-789",
        "startDate": "2023-01-01",
        "endDate": "2023-12-31",
        "rentAmount": 1200,
        "paymentDue": "2023-11-01",
        "status": "Active",
        "deposit": 1200,
        "paymentHistory": [
            {"date": "2023-10-01", "amount": 1200, "status": "Paid"},
            {"date": "2023-09-01", "amount": 1200, "status": "Paid"}
        ]
    },
    {
        "id": 1002,
        "property": "Ocean View Villa",
        "propertyId": 2,
        "unit": "2",
        "tenant": "Jane Smith",
        "tenantId": "user-456",
        "startDate": "2023-03-15",
        "endDate": "2024-03-14",
        "rentAmount": 2500,
        "paymentDue": "2023-11-15",
        "status": "Active",
        "deposit": 2500,
        "paymentHistory": [
            {"date": "2023-10-15", "amount": 2500, "status": "Paid"},
            {"date": "2023-09-15", "amount": 2500, "status": "Paid"}
        ]
    }
]

# OTP storage
otp_storage = {}

# Routes
@app.route('/')
def home():
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    return send_from_directory('static', 'login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return send_from_directory('static', 'register.html')

@app.route('/terms', methods=['GET'])
def terms_page():
    return send_from_directory('static', 'terms.html')

@app.route('/privacy', methods=['GET'])
def privacy_page():
    return send_from_directory('static', 'privacy.html')

@app.route('/dashboard')
def dashboard_page():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    # Redirect based on user role
    user_role = session.get('role')
    if user_role == 'admin':
        return redirect(url_for('admin_dashboard_page'))
    elif user_role == 'staff':
        return redirect(url_for('staff_dashboard_page'))
    elif user_role == 'tenant':
        return redirect(url_for('tenant_dashboard_page'))
    else:
        return send_from_directory('static', 'dashboard.html')

@app.route('/admin-dashboard')
def admin_dashboard_page():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    return send_from_directory('static', 'admin-dashboard.html')

@app.route('/staff-dashboard')
def staff_dashboard_page():
    if 'user' not in session or session.get('role') != 'staff':
        return redirect(url_for('login_page'))
    return send_from_directory('static', 'staff-dashboard.html')

@app.route('/tenant-dashboard')
def tenant_dashboard_page():
    if 'user' not in session or session.get('role') != 'tenant':
        return redirect(url_for('login_page'))
    return send_from_directory('static', 'tenant-dashboard.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Rental Management API is running"}), 200

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        firstName = data.get('firstName')
        lastName = data.get('lastName')
        role = data.get('role', 'tenant')  # Default to tenant
        agreeToTerms = data.get('agreeToTerms', False)

        # Validate input
        if not all([email, password, firstName, lastName]):
            return jsonify({"error": "All fields are required"}), 400

        if not agreeToTerms:
            return jsonify({"error": "You must agree to the Terms and Privacy Policy"}), 400

        # Validate password using function from auth.py
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({"error": message}), 400

        # Check if user already exists
        if email in mock_users:
            return jsonify({"error": "User already exists"}), 400

        # Create user (in production, use Firebase Auth)
        user_uid = f"mock-uid-{len(mock_users)}"
        mock_users[email] = {
            "password": password,  # In production, this would be hashed
            "firstName": firstName,
            "lastName": lastName,
            "role": role,
            "uid": user_uid,
            "emailVerified": False
        }

        # Store user in session
        session['user'] = email
        session['role'] = role
        session['firstName'] = firstName
        session['uid'] = user_uid

        return jsonify({
            "message": "User created successfully",
            "user": {
                "email": email,
                "firstName": firstName,
                "lastName": lastName,
                "role": role,
                "uid": user_uid
            },
            "redirect": f"/{role}-dashboard"  # Tell frontend where to redirect
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        provider = data.get('provider', 'email')  # 'email' or 'google'

        # Validate input
        if not email:
            return jsonify({"error": "Email is required"}), 400

        if provider == 'email' and not password:
            return jsonify({"error": "Password is required"}), 400

        # Google OAuth login simulation
        if provider == 'google':
            # In a real implementation, verify the Google ID token
            id_token = data.get('idToken')
            # For demo, we'll just check if the user exists or create a new one
            if email not in mock_users:
                # Create a new user with Google auth
                firstName = data.get('firstName', 'Google')
                lastName = data.get('lastName', 'User')
                user_uid = f"google-uid-{len(mock_users)}"
                
                mock_users[email] = {
                    "password": None,
                    "firstName": firstName,
                    "lastName": lastName,
                    "role": 'tenant',  # Default role for Google signups
                    "uid": user_uid,
                    "emailVerified": True
                }
            
            user = mock_users[email]
        else:
            # Email/password login
            user = mock_users.get(email)
            if not user or user['password'] != password:
                return jsonify({"error": "Invalid email or password"}), 401

        # Store user in session
        session['user'] = email
        session['role'] = user['role']
        session['firstName'] = user['firstName']
        session['uid'] = user['uid']

        return jsonify({
            "message": "Login successful",
            "user": {
                "email": email,
                "firstName": user['firstName'],
                "lastName": user['lastName'],
                "role": user['role'],
                "uid": user['uid']
            },
            "redirect": f"/{user['role']}-dashboard"  # Tell frontend where to redirect
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # For security, don't reveal if email exists or not
        if email not in mock_users:
            return jsonify({"message": "If the email exists, a reset code has been sent"}), 200

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        # Store OTP
        otp_storage[email] = {
            "otp": otp,
            "expiry": otp_expiry
        }

        # Send OTP via email using function from auth.py
        if send_otp_email(email, otp):
            return jsonify({"message": "If the email exists, a reset code has been sent"}), 200
        else:
            return jsonify({"error": "Failed to send OTP. Please try again later."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')

        if not email or not otp:
            return jsonify({"error": "Email and OTP are required"}), 400

        if email not in otp_storage:
            return jsonify({"error": "Invalid or expired OTP"}), 400

        otp_data = otp_storage[email]
        
        # Check if OTP is expired
        if datetime.datetime.now() > otp_data["expiry"]:
            del otp_storage[email]
            return jsonify({"error": "OTP has expired"}), 400

        # Verify OTP
        if otp_data["otp"] == otp:
            # Create a reset token (in real app, use JWT)
            reset_token = f"reset-token-{random.randint(1000, 9999)}"
            otp_data["reset_token"] = reset_token
            return jsonify({"message": "OTP verified", "resetToken": reset_token}), 200
        else:
            return jsonify({"error": "Invalid OTP"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        reset_token = data.get('resetToken')
        new_password = data.get('newPassword')

        if not all([email, reset_token, new_password]):
            return jsonify({"error": "All fields are required"}), 400

        # Validate password using function from auth.py
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({"error": message}), 400

        if email not in otp_storage:
            return jsonify({"error": "Invalid reset request"}), 400

        otp_data = otp_storage[email]
        
        if "reset_token" not in otp_data or otp_data["reset_token"] != reset_token:
            return jsonify({"error": "Invalid reset token"}), 400

        # Update password
        if email in mock_users:
            mock_users[email]["password"] = new_password
            # Clean up OTP data
            del otp_storage[email]
            return jsonify({"message": "Password reset successfully"}), 200
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logout successful"}), 200

@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_email = session['user']
    user = mock_users.get(user_email)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    return jsonify({
        "email": user_email,
        "firstName": user['firstName'],
        "lastName": user['lastName'],
        "role": user['role'],
        "uid": user['uid']
    }), 200

@app.route('/api/admin/dashboard', methods=['GET'])
@requires_role('admin')
def admin_dashboard():
    # Calculate stats
    total_users = len(mock_users)
    total_properties = len(mock_properties)
    active_leases = len([lease for lease in mock_leases if lease['status'] == 'Active'])
    maintenance_requests = len(mock_maintenance)
    
    # Get recent activity
    recent_activity = [
        {"action": "New user registration", "details": "John Doe registered as a tenant", "timestamp": "2 hours ago"},
        {"action": "Lease agreement signed", "details": "Apartment 4B lease agreement completed", "timestamp": "5 hours ago"},
        {"action": "Maintenance request", "details": "Plumbing issue reported in Unit 2C", "timestamp": "Yesterday"},
        {"action": "Payment received", "details": "Rent payment from Jane Smith for Ocean View Villa", "timestamp": "Yesterday"}
    ]
    
    return jsonify({
        "message": "Welcome to admin dashboard",
        "stats": {
            "users": total_users,
            "properties": total_properties,
            "activeLeases": active_leases,
            "maintenanceRequests": maintenance_requests
        },
        "recentActivity": recent_activity
    }), 200

@app.route('/api/admin/properties', methods=['GET'])
@requires_role('admin')
def get_properties():
    return jsonify({
        "properties": mock_properties
    }), 200

@app.route('/api/admin/users', methods=['GET'])
@requires_role('admin')
def get_users():
    # Convert mock_users to list format
    users_list = []
    for email, user_data in mock_users.items():
        users_list.append({
            "email": email,
            "firstName": user_data["firstName"],
            "lastName": user_data["lastName"],
            "role": user_data["role"],
            "uid": user_data["uid"],
            "status": "Active"  # Default status
        })
    
    return jsonify({
        "users": users_list
    }), 200

@app.route('/api/admin/maintenance', methods=['GET'])
@requires_role('admin')
def get_maintenance_requests():
    return jsonify({
        "maintenanceRequests": mock_maintenance
    }), 200

@app.route('/api/admin/leases', methods=['GET'])
@requires_role('admin')
def get_leases():
    return jsonify({
        "leases": mock_leases
    }), 200

@app.route('/api/staff/dashboard', methods=['GET'])
@requires_role('staff')
def staff_dashboard():
    # For staff, only show tasks assigned to them
    staff_name = session.get('firstName', 'Staff') + " " + session.get('lastName', 'Member')
    assigned_tasks = [task for task in mock_maintenance if task.get('assignedTo') == staff_name]
    
    return jsonify({
        "message": "Welcome to staff dashboard",
        "tasks": {
            "pendingApprovals": 2,
            "maintenanceRequests": len(assigned_tasks),
            "newApplications": 3
        },
        "assignedTasks": assigned_tasks
    }), 200

@app.route('/api/tenant/dashboard', methods=['GET'])
@requires_role('tenant')
def tenant_dashboard():
    # For tenant, show their lease information
    tenant_id = session.get('uid')
    tenant_leases = [lease for lease in mock_leases if lease.get('tenantId') == tenant_id]
    
    if tenant_leases:
        lease_info = tenant_leases[0]
    else:
        lease_info = {
            "property": "No active lease",
            "rentDue": "N/A",
            "balance": 0,
            "maintenanceRequests": 0
        }
    
    return jsonify({
        "message": "Welcome to tenant dashboard",
        "leaseInfo": lease_info
    }), 200

@app.route('/api/properties', methods=['GET'])
@requires_role(['admin', 'staff', 'tenant'])
def get_all_properties():
    # For tenants, only show properties they have leases for
    user_role = session.get('role')
    user_uid = session.get('uid')
    
    if user_role == 'tenant':
        tenant_properties = [lease['propertyId'] for lease in mock_leases if lease.get('tenantId') == user_uid]
        filtered_properties = [prop for prop in mock_properties if prop['id'] in tenant_properties]
        return jsonify({"properties": filtered_properties}), 200
    else:
        return jsonify({"properties": mock_properties}), 200

@app.route('/api/maintenance', methods=['POST'])
@requires_role(['admin', 'tenant'])
def create_maintenance_request():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['propertyId', 'unit', 'issue', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create new maintenance request
        new_request = {
            "id": max([req['id'] for req in mock_maintenance], default=100) + 1,
            "propertyId": data['propertyId'],
            "property": next((prop['name'] for prop in mock_properties if prop['id'] == data['propertyId']), "Unknown Property"),
            "unit": data['unit'],
            "issue": data['issue'],
            "description": data['description'],
            "reportedBy": session.get('firstName', 'User') + " " + session.get('lastName', ''),
            "reportedById": session.get('uid'),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "status": "Pending",
            "priority": data.get('priority', 'Medium'),
            "assignedTo": None
        }
        
        mock_maintenance.append(new_request)
        
        return jsonify({
            "message": "Maintenance request created successfully",
            "request": new_request
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/maintenance/<int:request_id>', methods=['PUT'])
@requires_role(['admin', 'staff'])
def update_maintenance_request(request_id):
    try:
        data = request.get_json()
        
        # Find the maintenance request
        request_index = None
        for i, req in enumerate(mock_maintenance):
            if req['id'] == request_id:
                request_index = i
                break
        
        if request_index is None:
            return jsonify({"error": "Maintenance request not found"}), 404
        
        # Update the request
        if 'status' in data:
            mock_maintenance[request_index]['status'] = data['status']
        
        if 'assignedTo' in data:
            mock_maintenance[request_index]['assignedTo'] = data['assignedTo']
        
        if 'priority' in data:
            mock_maintenance[request_index]['priority'] = data['priority']
        
        return jsonify({
            "message": "Maintenance request updated successfully",
            "request": mock_maintenance[request_index]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
