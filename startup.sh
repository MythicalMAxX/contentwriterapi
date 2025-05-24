#!/bin/bash

# Set the correct paths for Azure App Service
export PYTHONPATH=/home/site/wwwroot
export PATH="$PATH:/home/site/wwwroot/antenv/bin"

# Activate the Python virtual environment if it exists
if [ -d /home/site/wwwroot/antenv ]; then
    source /home/site/wwwroot/antenv/bin/activate
fi

# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install pydantic-core explicitly first
pip install --only-binary :all: pydantic-core==2.0.2

# Install pydantic with specific version
pip install --no-deps pydantic==2.0.3

# Install dependencies - using --no-build-isolation to avoid Rust compilation issues
pip install --no-build-isolation -r requirements.txt

# Start the application with Gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 