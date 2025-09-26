from flask import Blueprint, request, jsonify
from firebase_admin import storage
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

bp = Blueprint('file_upload', __name__, url_prefix='/api/files')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'images': ['png', 'jpg', 'jpeg', 'gif', 'bmp'],
    'documents': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
    'archives': ['zip', 'rar']
}

def allowed_file(filename, file_type='images'):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, [])

def upload_file_to_storage(file, folder_name, user_id):
    try:
        # Generate a unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # Create file path
        file_path = f"{folder_name}/{user_id}/{unique_filename}"
        
        # Get bucket
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        
        # Upload file
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Make the file publicly accessible (optional)
        blob.make_public()
        
        # Return public URL
        return blob.public_url
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

@bp.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file is in the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id')
        file_type = request.form.get('file_type', 'images')
        folder_name = request.form.get('folder_name', 'general')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename, file_type):
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Upload to Firebase Storage
            file_url = upload_file_to_storage(file, folder_name, user_id)
            
            if file_url:
                # Save file metadata to database if needed
                return jsonify({
                    'message': 'File uploaded successfully',
                    'file_url': file_url,
                    'filename': filename
                }), 200
            else:
                return jsonify({'error': 'Failed to upload file'}), 500
        else:
            return jsonify({'error': 'File type not allowed'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/lease/<user_id>', methods=['POST'])
def upload_lease_document(user_id):
    try:
        if 'lease_document' not in request.files:
            return jsonify({'error': 'No lease document provided'}), 400
        
        file = request.files['lease_document']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename, 'documents'):
            # Upload to Firebase Storage
            file_url = upload_file_to_storage(file, 'leases', user_id)
            
            if file_url:
                # Update user record with lease document URL
                from firebase_admin import db
                ref = db.reference(f'users/{user_id}')
                ref.update({
                    'lease_document_url': file_url,
                    'lease_upload_date': datetime.now().isoformat()
                })
                
                return jsonify({
                    'message': 'Lease document uploaded successfully',
                    'file_url': file_url
                }), 200
            else:
                return jsonify({'error': 'Failed to upload lease document'}), 500
        else:
            return jsonify({'error': 'Only PDF and document files are allowed'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/maintenance/<user_id>', methods=['POST'])
def upload_maintenance_photo(user_id):
    try:
        if 'maintenance_photo' not in request.files:
            return jsonify({'error': 'No maintenance photo provided'}), 400
        
        file = request.files['maintenance_photo']
        request_id = request.form.get('request_id')
        
        if not request_id:
            return jsonify({'error': 'Maintenance request ID is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename, 'images'):
            # Upload to Firebase Storage
            file_url = upload_file_to_storage(file, 'maintenance', user_id)
            
            if file_url:
                # Update maintenance request with photo URL
                from firebase_admin import db
                ref = db.reference(f'maintenance_requests/{user_id}/{request_id}')
                
                # Get existing photos or initialize empty array
                request_data = ref.get() or {}
                photos = request_data.get('photos', [])
                photos.append(file_url)
                
                ref.update({
                    'photos': photos,
                    'last_updated': datetime.now().isoformat()
                })
                
                return jsonify({
                    'message': 'Maintenance photo uploaded successfully',
                    'file_url': file_url
                }), 200
            else:
                return jsonify({'error': 'Failed to upload maintenance photo'}), 500
        else:
            return jsonify({'error': 'Only image files are allowed'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500