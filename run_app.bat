@echo off
cd /d "%~dp0"
if exist "dist\EmailApp.exe" (
    start "" /B "dist\EmailApp.exe"
) else (
    echo EmailApp.exe not found in dist directory
    pause
)