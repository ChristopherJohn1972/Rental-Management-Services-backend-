# app/firebase_config.py
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from main.py
from main import app

# Export the app for gunicorn
# This file now makes 'app.firebase_config:app' point to your FastAPI app
