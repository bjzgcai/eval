#!/bin/bash

# Quick start script for GitHub Data Collector API Server

echo "=================================================="
echo "GitHub Data Collector API Server - Quick Start"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Set GitHub token if provided
if [ -n "$1" ]; then
    export GITHUB_TOKEN="$1"
    echo "GitHub token configured"
fi

# Set port if provided as second argument, otherwise default to 8000
if [ -n "$2" ]; then
    export PORT="$2"
fi

# Start the server
echo ""
echo "=================================================="
echo "Starting server..."
echo "Note: If port is in use, it will auto-select the next available port"
echo "=================================================="
echo ""

python server.py
