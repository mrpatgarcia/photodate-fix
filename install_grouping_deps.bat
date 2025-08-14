@echo off
REM Install photo grouping dependencies in virtual environment

echo Installing photo grouping dependencies...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install the AI packages
echo Installing scikit-learn...
pip install scikit-learn>=1.3.0

echo Installing numpy...
pip install numpy>=1.24.0

echo Installing opencv-python-headless...
pip install opencv-python-headless>=4.8.0

REM Test imports
echo Testing package imports...
python -c "import cv2; print('✓ OpenCV version:', cv2.__version__)"
python -c "import sklearn; print('✓ scikit-learn version:', sklearn.__version__)"
python -c "import numpy; print('✓ NumPy version:', numpy.__version__)"

echo.
echo Photo grouping dependencies installed successfully!
echo You can now run: run_photo_processing.bat

pause