from flask import Blueprint, request, jsonify
from firebase_service import FirebaseService
from middleware.auth import token_required
from datetime import datetime

properties_bp = Blueprint('properties', __name__)

@properties_bp.route('/', methods=['GET'])
@token_required
def get_properties(user_data):
    try:
        db = FirebaseService.get_firestore()
        properties_ref = db.collection('properties')
        properties = []
        
        for doc in properties_ref.stream():
            property_data = doc.to_dict()
            properties.append({
                'id': doc.id,
                **property_data
            })
        
        return jsonify(properties), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch properties: {str(e)}'}), 500

@properties_bp.route('/<property_id>', methods=['GET'])
@token_required
def get_property(user_data, property_id):
    try:
        db = FirebaseService.get_firestore()
        property_ref = db.collection('properties').document(property_id)
        property_doc = property_ref.get()
        
        if not property_doc.exists:
            return jsonify({'error': 'Property not found'}), 404
        
        property_data = property_doc.to_dict()
        return jsonify({
            'id': property_doc.id,
            **property_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch property: {str(e)}'}), 500

@properties_bp.route('/', methods=['POST'])
@token_required
def create_property(user_data):
    try:
        data = request.get_json()
        required_fields = ['name', 'address', 'type', 'totalUnits']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        property_data = {
            'name': data['name'],
            'address': data['address'],
            'type': data['type'],
            'totalUnits': int(data['totalUnits']),
            'occupiedUnits': 0,
            'vacantUnits': int(data['totalUnits']),
            'description': data.get('description', ''),
            'status': 'active',
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }
        
        db = FirebaseService.get_firestore()
        doc_ref = db.collection('properties').document()
        doc_ref.set(property_data)
        
        return jsonify({
            'id': doc_ref.id,
            'message': 'Property created successfully',
            **property_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to create property: {str(e)}'}), 500

@properties_bp.route('/<property_id>', methods=['PUT'])
@token_required
def update_property(user_data, property_id):
    try:
        data = request.get_json()
        db = FirebaseService.get_firestore()
        property_ref = db.collection('properties').document(property_id)
        property_doc = property_ref.get()
        
        if not property_doc.exists:
            return jsonify({'error': 'Property not found'}), 404
        
        update_data = {
            'updatedAt': datetime.now().isoformat()
        }
        
        if 'name' in data:
            update_data['name'] = data['name']
        if 'address' in data:
            update_data['address'] = data['address']
        if 'type' in data:
            update_data['type'] = data['type']
        if 'totalUnits' in data:
            update_data['totalUnits'] = int(data['totalUnits'])
        if 'description' in data:
            update_data['description'] = data['description']
        if 'status' in data:
            update_data['status'] = data['status']
        
        property_ref.update(update_data)
        
        return jsonify({
            'message': 'Property updated successfully',
            'id': property_id,
            **update_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update property: {str(e)}'}), 500

@properties_bp.route('/<property_id>', methods=['DELETE'])
@token_required
def delete_property(user_data, property_id):
    try:
        db = FirebaseService.get_firestore()
        property_ref = db.collection('properties').document(property_id)
        property_doc = property_ref.get()
        
        if not property_doc.exists:
            return jsonify({'error': 'Property not found'}), 404
        
        # Check if property has tenants
        tenants_ref = db.collection('tenants').where('propertyId', '==', property_id)
        tenants = list(tenants_ref.stream())
        
        if tenants:
            return jsonify({'error': 'Cannot delete property with active tenants'}), 400
        
        property_ref.delete()
        
        return jsonify({'message': 'Property deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete property: {str(e)}'}), 500

@properties_bp.route('/<property_id>/units', methods=['GET'])
@token_required
def get_property_units(user_data, property_id):
    try:
        db = FirebaseService.get_firestore()
        units_ref = db.collection('units').where('propertyId', '==', property_id)
        units = []
        
        for doc in units_ref.stream():
            unit_data = doc.to_dict()
            units.append({
                'id': doc.id,
                **unit_data
            })
        
        return jsonify(units), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch units: {str(e)}'}), 500