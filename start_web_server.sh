#!/bin/bash

# Start the FragDropDetector Web Configuration Server

echo "Starting FragDropDetector Web Server..."

# Activate virtual environment
source venv/bin/activate

# Start the web server
python web_server.py