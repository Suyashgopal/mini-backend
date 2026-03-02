@echo off
echo Starting OCR Pharma Compliance Backend...
echo.

REM Navigate to project directory
cd /d "c:\Users\KIIT0001\Downloads\mini-backend-main\mini-backend-main"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Start the Flask backend
echo Starting Flask server on http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.
python src\app.py

pause
