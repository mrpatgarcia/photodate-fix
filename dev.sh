#!/bin/bash
# Pure Docker development workflow - no local Python dependencies needed

echo "🐳 PhotoDate Fix - Docker Development"
echo "=============================================="

# Create data directories if they don't exist
mkdir -p data/photos/unprocessed
mkdir -p data/photos/processed  
mkdir -p data/db
mkdir -p data/thumbs

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

echo ""
echo "🚀 Starting development container with live code updates..."
echo "   - Your code is mounted for live updates"
echo "   - Access at: http://localhost:5000"
echo "   - Press Ctrl+C to stop"
echo ""

# Start the development container
docker-compose -f docker-compose.dev.yml up --build