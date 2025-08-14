@echo off
REM Pure Docker development workflow - no local Python dependencies needed

echo 🐳 PhotoDate Fix - Docker Development
echo ==============================================

REM Create data directories if they don't exist
if not exist "data\photos\unprocessed" mkdir data\photos\unprocessed
if not exist "data\photos\processed" mkdir data\photos\processed
if not exist "data\db" mkdir data\db
if not exist "data\thumbs" mkdir data\thumbs

REM Create .env if it doesn't exist
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
) else (
    echo .env file already exists
)

echo.
echo 🚀 Starting development container with live code updates...
echo    - Your code is mounted for live updates
echo    - Access at: http://localhost:5000
echo    - Press Ctrl+C to stop
echo.

REM Start the development container
docker-compose -f docker-compose.dev.yml up --build