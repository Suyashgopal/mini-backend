@echo off
echo ==========================================
echo OCR Pharma Compliance Backend Manager
echo ==========================================
echo.
echo 1. Start Backend
echo 2. Stop Backend  
echo 3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Starting backend...
    call start_backend.bat
) else if "%choice%"=="2" (
    echo.
    echo Stopping backend...
    call stop_backend.bat
) else if "%choice%"=="3" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice. Please try again.
    pause
    call menu.bat
)
