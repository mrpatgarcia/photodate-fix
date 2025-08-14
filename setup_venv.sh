#!/bin/bash

echo "Setting up virtual environment for Photo Date Scanner..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

echo ""
echo "Virtual environment setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application:"
echo "  python app.py"
echo ""