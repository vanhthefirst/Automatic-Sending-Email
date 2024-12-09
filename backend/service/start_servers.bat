/*For Windows Services*/
@echo off
cd /d %~dp0
start /b cmd /c "cd src && npm run dev"
start /b cmd /c "uvicorn backend.api:app --host 0.0.0.0 --port 8000"