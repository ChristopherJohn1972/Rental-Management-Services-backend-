import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastAPI app from main
from main import app

# Export for gunicorn
# Now app.firebase_config:app points to your FastAPI app
