from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import MaintenanceRequest, User
from .firebase_config import storage_bucket
import uuid
from datetime import datetime

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/', methods=['GET'])
@jwt_required()
def get_maintenance_requests():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        if current_user.get('role') in ['admin', 'staff']:
            # Admin/staff can see all requests
            requests_ref = db_ref.child('maintenance_requests')
            requests = requests_ref.get() or {}
        else:
            # Tenants can only see their own requests
            requests = MaintenanceRequest.get_by_user(current_user_id)
        
        return jsonify({
            'success': True,
            'requests': requests
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving maintenance requests: {str(e)}'
        }), 500

@maintenance_bp.route('/', methods=['POST'])
@jwt_required()
def create_maintenance_request():
    try:
        current_user_id = get_jwt_identity()
        
        request_data = request.json
        request_data['user_id'] = current_user_id
        request_data['user_name'] = User.get(current_user_id).get('name', 'Unknown')
        
        # Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # Generate unique filename
                filename = f"maintenance/{uuid.uuid4()}_{file.filename}"
                blob = storage_bucket.blob(filename)
                blob.upload_from_file(file)
                blob.make_public()
                request_data['photo_url'] = blob.public_url
        
        request = MaintenanceRequest.create(request_data)
        
        return jsonify({
            'success': True,
            'message': 'Maintenance request created successfully',
            'request': request
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating maintenance request: {str(e)}'
        }), 500

@maintenance_bp.route('/<request_id>', methods=['GET'])
@jwt_required()
def get_maintenance_request(request_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        request_ref = db_ref.child('maintenance_requests').child(request_id)
        request = request_ref.get()
        
        if not request:
            return jsonify({
                'success': False,
                'message': 'Maintenance request not found'
            }), 404
        
        # Check if user has access to this request
        if current_user.get('role') not in ['admin', 'staff'] and request.get('user_id') != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        return jsonify({
            'success': True,
            'request': request
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving maintenance request: {str(e)}'
        }), 500

@maintenance_bp.route('/<request_id>', methods=['PUT'])
@jwt_required()
def update_maintenance_request(request_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        request_ref = db_ref.child('maintenance_requests').child(request_id)
        request = request_ref.get()
        
        if not request:
            return jsonify({
                'success': False,
                'message': 'Maintenance request not found'
            }), 404
        
        # Check if user has access to update this request
        if current_user.get('role') not in ['admin', 'staff'] and request.get('user_id') != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        updates = request.json
        updates['updated_at'] = datetime.now().isoformat()
        
        # Only admin/staff can change status
        if current_user.get('role') not in ['admin', 'staff']:
            updates.pop('status', None)
        
        request_ref.update(updates)
        updated_request = request_ref.get()
        
        return jsonify({
            'success': True,
            'message': 'Maintenance request updated successfully',
            'request': updated_request
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating maintenance request: {str(e)}'
        }), 500

@maintenance_bp.route('/<request_id>', methods=['DELETE'])
@jwt_required()
def delete_maintenance_request(request_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        request_ref = db_ref.child('maintenance_requests').child(request_id)
        request = request_ref.get()
        
        if not request:
            return jsonify({
                'success': False,
                'message': 'Maintenance request not found'
            }), 404
        
        # Only admin can delete requests
        if current_user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        request_ref.delete()
        
        return jsonify({
            'success': True,
            'message': 'Maintenance request deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting maintenance request: {str(e)}'
        }), 500
