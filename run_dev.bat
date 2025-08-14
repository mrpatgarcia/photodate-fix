@echo off
echo 🔧 PhotoDate Fix - Development Runner
echo.

:: Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

:: Run the development server
echo.
echo 🚀 Starting development server...
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop the server
echo.

python run_dev.py

pause