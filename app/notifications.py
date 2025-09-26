from flask import Blueprint, request, jsonify
from firebase_admin import db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import json

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

# Email notification function
def send_email(to_email, subject, message, is_html=False):
    try:
        # Email configuration
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_host = os.getenv('EMAIL_HOST')
        email_port = int(os.getenv('EMAIL_PORT', 587))
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        if is_html:
            msg.attach(MIMEText(message, 'html'))
        else:
            msg.attach(MIMEText(message, 'plain'))
        
        # Send email
        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Push notification function (for mobile apps)
def send_push_notification(user_id, title, message, data=None):
    try:
        # This would integrate with FCM (Firebase Cloud Messaging)
        # For now, we'll just log to the database
        ref = db.reference(f'notifications/{user_id}')
        notification_id = ref.push().key
        
        notification_data = {
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        if data:
            notification_data['data'] = json.dumps(data)
        
        ref.child(notification_id).set(notification_data)
        
        return True
    except Exception as e:
        print(f"Error sending push notification: {e}")
        return False

# API Routes
@bp.route('/email', methods=['POST'])
def send_email_notification():
    try:
        data = request.json
        to_email = data.get('to_email')
        subject = data.get('subject')
        message = data.get('message')
        is_html = data.get('is_html', False)
        
        if not all([to_email, subject, message]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        success = send_email(to_email, subject, message, is_html)
        
        if success:
            return jsonify({'message': 'Email sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/push', methods=['POST'])
def send_push_notification_route():
    try:
        data = request.json
        user_id = data.get('user_id')
        title = data.get('title')
        message = data.get('message')
        notification_data = data.get('data')
        
        if not all([user_id, title, message]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        success = send_push_notification(user_id, title, message, notification_data)
        
        if success:
            return jsonify({'message': 'Push notification sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send push notification'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/user/<user_id>', methods=['GET'])
def get_user_notifications(user_id):
    try:
        ref = db.reference(f'notifications/{user_id}')
        notifications = ref.order_by_child('timestamp').limit_to_last(20).get()
        
        if notifications:
            # Convert to list and add IDs
            notifications_list = []
            for notif_id, notif_data in notifications.items():
                notif_data['id'] = notif_id
                notifications_list.append(notif_data)
            
            return jsonify(notifications_list), 200
        else:
            return jsonify([]), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/user/<user_id>/read/<notification_id>', methods=['POST'])
def mark_notification_as_read(user_id, notification_id):
    try:
        ref = db.reference(f'notifications/{user_id}/{notification_id}')
        ref.update({'read': True})
        
        return jsonify({'message': 'Notification marked as read'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500