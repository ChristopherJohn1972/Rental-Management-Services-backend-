from flask import Flask
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # App configuration
    app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'
    
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
    
    # Register blueprints or import routes here
    from . import notifications, file_upload, payments
    
    # Register routes
    app.register_blueprint(notifications.bp)
    app.register_blueprint(file_upload.bp)
    app.register_blueprint(payments.bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)