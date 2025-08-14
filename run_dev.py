#!/usr/bin/env python3
"""
Development runner that handles missing dependencies gracefully
"""
import sys
import os
import subprocess

def install_missing_deps():
    """Install missing dependencies"""
    try:
        # Try installing from requirements.txt
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        return False

def check_and_install_deps():
    """Check for missing dependencies and install if needed"""
    missing_deps = []
    
    # Check for critical dependencies
    try:
        import flask
    except ImportError:
        missing_deps.append('flask')
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        missing_deps.append('apscheduler')
    
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append('pillow')
    
    if missing_deps:
        print(f"Missing dependencies: {', '.join(missing_deps)}")
        print("Installing dependencies...")
        return install_missing_deps()
    
    return True

def run_app():
    """Run the Flask application"""
    # Add src directory to Python path
    src_dir = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_dir)
    
    # Change to src directory
    os.chdir(src_dir)
    
    # Import and run the app
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"Error importing app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Development runner for FastFoto Date Scanner")
    
    if not check_and_install_deps():
        print("❌ Failed to install dependencies. Please run:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    print("🚀 Starting development server...")
    run_app()