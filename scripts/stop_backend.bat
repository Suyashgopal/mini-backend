@echo off
echo Stopping OCR Pharma Compliance Backend...

REM Kill all Python processes
taskkill /F /IM python.exe >nul 2>&1

REM Also kill any Flask processes
taskkill /F /IM flask.exe >nul 2>&1

echo Backend stopped.
timeout /t 2 >nul
