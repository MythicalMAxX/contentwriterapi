import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Import the app from the app module
from app.main import app

# This is used by Azure's Gunicorn configuration
application = app
