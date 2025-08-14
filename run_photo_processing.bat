@echo off
echo Starting photo processing and similarity analysis...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtual environment found. Make sure dependencies are installed.
)

REM Run the photo processing script from src directory with data folder
python src/run_photo_processing.py --photos-dir data/photos/unprocessed %*

REM Keep window open if run manually
if "%1"=="" pause