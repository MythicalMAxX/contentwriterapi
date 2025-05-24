#!/bin/bash

# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install dependencies - using --no-build-isolation to avoid Rust compilation issues
pip install --no-build-isolation -r requirements.txt

# Start the application with Gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 