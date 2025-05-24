#!/bin/bash

# Navigate to the site directory
cd $HOME/site/wwwroot

# Create Python virtual environment if it doesn't exist
if [ ! -d antenv ]; then
    echo "Creating Python virtual environment..."
    python -m venv antenv
fi

# Activate the virtual environment
source antenv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install --only-binary :all: pydantic-core==2.0.2
pip install --no-deps pydantic==2.0.3
pip install --no-build-isolation -r requirements.txt

# Make startup script executable
chmod +x startup.sh

echo "Deployment completed successfully!" 