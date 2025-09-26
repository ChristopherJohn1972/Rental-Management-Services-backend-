from flask import request, jsonify
from firebase_service import FirebaseService
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Authorization token is required'}), 401
        
        try:
            # Verify the token
            auth = FirebaseService.get_auth()
            user_data = auth.verify_id_token(token)
            request.user_data = user_data
            
        except Exception as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        
        return f(*args, **kwargs)
    
    return decorated