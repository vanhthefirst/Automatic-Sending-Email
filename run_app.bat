@echo off
title Automatic Email System
cd /d "%~dp0"

echo Checking application files...
if not exist "dist\EmailApp.exe" (
    echo Error: EmailApp.exe not found in dist directory
    echo Please ensure the application is properly installed.
    echo.
    echo Press any key to exit...
    pause > nul
    exit /b 1
)

echo Starting Automatic Email System...
echo Please wait while the application initializes...

rem Check if the process is already running
tasklist /FI "IMAGENAME eq EmailApp.exe" 2>NUL | find /I /N "EmailApp.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo.
    echo Warning: Application is already running!
    echo Please check your system tray or task manager.
    echo.
    echo Press any key to exit...
    pause > nul
    exit /b 1
)

start "" /B "dist\EmailApp.exe"
echo.
echo Application started successfully!
echo The web interface will open in your default browser.
echo You can minimize this window.
echo.
echo Press any key to exit this launcher...
pause > nul