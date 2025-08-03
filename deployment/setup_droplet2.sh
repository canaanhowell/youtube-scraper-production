#!/bin/bash

# Setup script for droplet2 YouTube scraper

echo "Setting up YouTube scraper on droplet2..."

# Create necessary directories
mkdir -p /opt/youtube_app/{src,data,logs}
mkdir -p /opt/youtube_app/src/{scripts,utils,config}

# Activate virtual environment
cd /opt/youtube_app
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install playwright==1.48.0
pip install requests==2.32.3
pip install firebase-admin==6.5.0
pip install python-dotenv==1.0.1
pip install aiofiles==24.1.0
pip install asyncio

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps

echo "Setup complete!"