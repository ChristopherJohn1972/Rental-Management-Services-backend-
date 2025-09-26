from flask import Blueprint, request, jsonify
from firebase_admin import db
import os
import stripe
import requests
from datetime import datetime
import json

bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@bp.route('/stripe/create-payment-intent', methods=['POST'])
def create_stripe_payment_intent():
    try:
        data = request.json
        amount = data.get('amount')
        currency = data.get('currency', 'usd')
        user_id = data.get('user_id')
        description = data.get('description', 'Rental Payment')
        
        if not amount or not user_id:
            return jsonify({'error': 'Amount and user ID are required'}), 400
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency,
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'user_id': user_id,
                'description': description
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret,
            'paymentIntentId': intent.id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/stripe/confirm-payment', methods=['POST'])
def confirm_stripe_payment():
    try:
        data = request.json
        payment_intent_id = data.get('payment_intent_id')
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not all([payment_intent_id, user_id, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Retrieve the payment intent
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Save payment to database
            ref = db.reference(f'payments/{user_id}')
            payment_id = ref.push().key
            
            payment_data = {
                'payment_id': payment_id,
                'amount': amount,
                'currency': intent.currency,
                'method': 'stripe',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'stripe_payment_intent_id': payment_intent_id
            }
            
            ref.child(payment_id).set(payment_data)
            
            # Update user's balance
            user_ref = db.reference(f'users/{user_id}')
            user_data = user_ref.get() or {}
            current_balance = user_data.get('balance', 0)
            new_balance = max(0, current_balance - amount)
            user_ref.update({'balance': new_balance})
            
            # Send payment confirmation
            from .notifications import send_email
            user_email = user_data.get('email')
            if user_email:
                send_email(
                    user_email,
                    'Payment Confirmation',
                    f'Your payment of ${amount} has been processed successfully.'
                )
            
            return jsonify({
                'message': 'Payment confirmed successfully',
                'payment_id': payment_id
            }), 200
        else:
            return jsonify({'error': 'Payment not successful'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/paypal/create-order', methods=['POST'])
def create_paypal_order():
    try:
        data = request.json
        amount = data.get('amount')
        currency = data.get('currency', 'USD')
        
        if not amount:
            return jsonify({'error': 'Amount is required'}), 400
        
        # Get access token
        auth = requests.auth.HTTPBasicAuth(
            os.getenv('PAYPAL_CLIENT_ID'),
            os.getenv('PAYPAL_CLIENT_SECRET')
        )
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency,
                    'value': str(amount)
                }
            }]
        }
        
        response = requests.post(
            'https://api-m.sandbox.paypal.com/v2/checkout/orders',
            auth=auth,
            headers=headers,
            json=data
        )
        
        if response.status_code == 201:
            order_data = response.json()
            return jsonify({
                'orderID': order_data['id']
            }), 200
        else:
            return jsonify({'error': 'Failed to create PayPal order'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/paypal/capture-order', methods=['POST'])
def capture_paypal_order():
    try:
        data = request.json
        order_id = data.get('orderID')
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not all([order_id, user_id, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get access token
        auth = requests.auth.HTTPBasicAuth(
            os.getenv('PAYPAL_CLIENT_ID'),
            os.getenv('PAYPAL_CLIENT_SECRET')
        )
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture',
            auth=auth,
            headers=headers
        )
        
        if response.status_code == 201:
            # Save payment to database
            ref = db.reference(f'payments/{user_id}')
            payment_id = ref.push().key
            
            payment_data = {
                'payment_id': payment_id,
                'amount': amount,
                'currency': 'USD',  # PayPal default
                'method': 'paypal',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'paypal_order_id': order_id
            }
            
            ref.child(payment_id).set(payment_data)
            
            # Update user's balance
            user_ref = db.reference(f'users/{user_id}')
            user_data = user_ref.get() or {}
            current_balance = user_data.get('balance', 0)
            new_balance = max(0, current_balance - amount)
            user_ref.update({'balance': new_balance})
            
            return jsonify({
                'message': 'Payment captured successfully',
                'payment_id': payment_id
            }), 200
        else:
            return jsonify({'error': 'Failed to capture PayPal order'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/mpesa/payment-request', methods=['POST'])
def mpesa_payment_request():
    try:
        # This is a simplified version - real implementation would require
        # more complex integration with Safaricom's API
        data = request.json
        amount = data.get('amount')
        phone_number = data.get('phone_number')
        user_id = data.get('user_id')
        
        if not all([amount, phone_number, user_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # In a real implementation, you would:
        # 1. Get access token from Safaricom
        # 2. Initiate STK push
        # 3. Handle callback with payment result
        
        # For now, we'll simulate a successful payment
        ref = db.reference(f'payments/{user_id}')
        payment_id = ref.push().key
        
        payment_data = {
            'payment_id': payment_id,
            'amount': amount,
            'currency': 'KES',
            'method': 'mpesa',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'phone_number': phone_number
        }
        
        ref.child(payment_id).set(payment_data)
        
        # Update user's balance
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get() or {}
        current_balance = user_data.get('balance', 0)
        new_balance = max(0, current_balance - amount)
        user_ref.update({'balance': new_balance})
        
        return jsonify({
            'message': 'MPesa payment request sent successfully',
            'payment_id': payment_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/history/<user_id>', methods=['GET'])
def get_payment_history(user_id):
    try:
        ref = db.reference(f'payments/{user_id}')
        payments = ref.order_by_child('timestamp').limit_to_last(20).get()
        
        if payments:
            # Convert to list and add IDs
            payments_list = []
            for payment_id, payment_data in payments.items():
                payment_data['id'] = payment_id
                payments_list.append(payment_data)
            
            return jsonify(payments_list), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/receipt/<user_id>/<payment_id>', methods=['GET'])
def generate_receipt(user_id, payment_id):
    try:
        ref = db.reference(f'payments/{user_id}/{payment_id}')
        payment_data = ref.get()
        
        if not payment_data:
            return jsonify({'error': 'Payment not found'}), 404
        
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get() or {}
        
        # Generate receipt HTML (simplified)
        receipt_html = f"""
        <html>
        <head><title>Payment Receipt</title></head>
        <body>
            <h1>Payment Receipt</h1>
            <p><strong>Receipt ID:</strong> {payment_id}</p>
            <p><strong>Date:</strong> {payment_data.get('timestamp', '')}</p>
            <p><strong>Tenant:</strong> {user_data.get('name', '')}</p>
            <p><strong>Property:</strong> {user_data.get('property_name', '')}</p>
            <p><strong>Amount:</strong> {payment_data.get('amount', 0)} {payment_data.get('currency', 'USD')}</p>
            <p><strong>Payment Method:</strong> {payment_data.get('method', '')}</p>
            <p><strong>Status:</strong> {payment_data.get('status', '')}</p>
        </body>
        </html>
        """
        
        return jsonify({
            'receipt_html': receipt_html,
            'payment_data': payment_data
        }), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500