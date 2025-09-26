from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import User

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        # Only admin can view all users
        if current_user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        # Get all users from Firebase
        users_ref = db_ref.child('users')
        users = users_ref.get()
        
        return jsonify({
            'success': True,
            'users': users
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving users: {str(e)}'
        }), 500

@users_bp.route('/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        # Users can only view their own profile, unless they're admin/staff
        if current_user_id != user_id and current_user.get('role') not in ['admin', 'staff']:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        user = User.get(user_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving user: {str(e)}'
        }), 500

@users_bp.route('/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        # Only admin can update other users
        if current_user_id != user_id and current_user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        updates = request.json
        
        # Remove fields that shouldn't be updated
        updates.pop('uid', None)
        updates.pop('email', None)
        updates.pop('created_at', None)
        
        success = User.update(user_id, updates)
        
        if success:
            user = User.get(user_id)
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': user
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update user'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating user: {str(e)}'
        }), 500

@users_bp.route('/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get(current_user_id)
        
        # Only admin can delete users
        if current_user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        # Delete user from Firebase
        db_ref.child('users').child(user_id).delete()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }), 500
