from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db, storage
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize Firebase
try:
    # For production, use service account key file
    cred = credentials.Certificate("serviceAccountKey.json")
except:
    # For development, use application default credentials
    cred = credentials.ApplicationDefault()

firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
})

# Mock user data - in a real app, this would come from a database
users = {
    'tenant1': {'password': 'password123', 'role': 'tenant', 'name': 'John Doe', 'apartment': 'Sunshine Apt #304'},
    'admin1': {'password': 'admin123', 'role': 'admin', 'name': 'Admin User'},
    'staff1': {'password': 'staff123', 'role': 'staff', 'name': 'Staff Member'}
}

# Helper functions
def get_user_data(user_id):
    """Get user data from Firebase"""
    try:
        ref = db.reference(f'users/{user_id}')
        return ref.get()
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None

def get_tenant_lease_data(user_id):
    """Get lease data for a tenant"""
    try:
        ref = db.reference(f'leases/{user_id}')
        return ref.get()
    except Exception as e:
        print(f"Error getting lease data: {e}")
        return None

def get_maintenance_requests(user_id, role):
    """Get maintenance requests based on user role"""
    try:
        if role == 'tenant':
            ref = db.reference(f'maintenance_requests/{user_id}')
        else:  # admin or staff
            ref = db.reference('maintenance_requests')
        return ref.get()
    except Exception as e:
        print(f"Error getting maintenance requests: {e}")
        return None

def get_payment_data(user_id, role):
    """Get payment data based on user role"""
    try:
        if role == 'tenant':
            ref = db.reference(f'payments/{user_id}')
        else:  # admin or staff
            ref = db.reference('payments')
        return ref.get()
    except Exception as e:
        print(f"Error getting payment data: {e}")
        return None

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username in users and users[username]['password'] == password:
        session['user_id'] = username
        session['user_role'] = users[username]['role']
        session['user_name'] = users[username]['name']
        return redirect(url_for('dashboard'))
    
    return render_template('login.html', error='Invalid credentials')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    user_role = session['user_role']
    
    # Get data based on user role
    if user_role == 'tenant':
        user_data = get_user_data(user_id)
        lease_data = get_tenant_lease_data(user_id)
        maintenance_data = get_maintenance_requests(user_id, user_role)
        payment_data = get_payment_data(user_id, user_role)
        
        return render_template('tenant_dashboard.html', 
                             user_data=user_data,
                             lease_data=lease_data,
                             maintenance_data=maintenance_data,
                             payment_data=payment_data)
    
    elif user_role == 'admin':
        # Admin sees all data
        all_users = db.reference('users').get()
        all_leases = db.reference('leases').get()
        maintenance_data = get_maintenance_requests(user_id, user_role)
        payment_data = get_payment_data(user_id, user_role)
        
        return render_template('admin_dashboard.html',
                             all_users=all_users,
                             all_leases=all_leases,
                             maintenance_data=maintenance_data,
                             payment_data=payment_data)
    
    elif user_role == 'staff':
        # Staff sees limited admin data
        all_users = db.reference('users').get()
        all_leases = db.reference('leases').get()
        maintenance_data = get_maintenance_requests(user_id, user_role)
        payment_data = get_payment_data(user_id, user_role)
        
        return render_template('staff_dashboard.html',
                             all_users=all_users,
                             all_leases=all_leases,
                             maintenance_data=maintenance_data,
                             payment_data=payment_data)

# API Routes for tenant actions
@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    data = request.json
    
    try:
        ref = db.reference(f'users/{user_id}')
        ref.update(data)
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_maintenance', methods=['POST'])
def submit_maintenance():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    data = request.json
    request_id = str(uuid.uuid4())
    
    try:
        ref = db.reference(f'maintenance_requests/{user_id}/{request_id}')
        data['submitted_at'] = datetime.now().isoformat()
        data['status'] = 'submitted'
        ref.set(data)
        return jsonify({'message': 'Maintenance request submitted successfully', 'request_id': request_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_lease', methods=['POST'])
def upload_lease():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    if 'lease_document' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['lease_document']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Upload to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(f'leases/{user_id}/{file.filename}')
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Make the file publicly accessible
        blob.make_public()
        
        # Update user record with lease document URL
        ref = db.reference(f'users/{user_id}')
        ref.update({
            'lease_document_url': blob.public_url,
            'lease_upload_date': datetime.now().isoformat()
        })
        
        return jsonify({'message': 'Lease document uploaded successfully', 'file_url': blob.public_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API Routes for admin/staff actions
@app.route('/api/update_maintenance_status', methods=['POST'])
def update_maintenance_status():
    if 'user_id' not in session or session['user_role'] not in ['admin', 'staff']:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.json
    tenant_id = data.get('tenant_id')
    request_id = data.get('request_id')
    status = data.get('status')
    notes = data.get('notes', '')
    
    try:
        ref = db.reference(f'maintenance_requests/{tenant_id}/{request_id}')
        updates = {
            'status': status,
            'updated_at': datetime.now().isoformat(),
            'updated_by': session['user_id']
        }
        
        if notes:
            updates['notes'] = notes
            
        ref.update(updates)
        return jsonify({'message': 'Maintenance status updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_tenant_data/<tenant_id>')
def get_tenant_data(tenant_id):
    if 'user_id' not in session or session['user_role'] not in ['admin', 'staff']:
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        user_data = get_user_data(tenant_id)
        lease_data = get_tenant_lease_data(tenant_id)
        maintenance_data = get_maintenance_requests(tenant_id, 'tenant')
        payment_data = get_payment_data(tenant_id, 'tenant')
        
        return jsonify({
            'user_data': user_data,
            'lease_data': lease_data,
            'maintenance_data': maintenance_data,
            'payment_data': payment_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'False').lower() == 'true')
