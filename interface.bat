@echo off
setlocal EnableDelayedExpansion

echo Starting build process...
echo Checking environment...

:: Check if npm is installed
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: npm is not installed or not in PATH
    exit /b 1
)

:: Clean up existing builds
echo Cleaning up previous builds...
if exist "dist" rmdir /s /q "dist"
if exist ".next" rmdir /s /q ".next"
if exist "out" rmdir /s /q "out"
if exist "standalone" rmdir /s /q "standalone"

:: Create fresh directories
echo Creating directories...
mkdir "dist"
mkdir "dist\.next"
mkdir "dist\public"

:: Install dependencies
echo Installing dependencies...
call npm install

:: Build Next.js application
echo Building Next.js application...
call npm run build

:: Create and prepare dist directory structure
echo Preparing distribution...
if exist ".next\static" (
    echo Copying static files...
    xcopy /E /I /Y ".next\static" "dist\.next\static\"
)

if exist ".next\server" (
    echo Copying server files...
    xcopy /E /I /Y ".next\server" "dist\.next\server\"
)

if exist ".next\cache" (
    echo Copying cache files...
    xcopy /E /I /Y ".next\cache" "dist\.next\cache\"
)

if exist "public" (
    echo Copying public files...
    xcopy /E /I /Y "public\*" "dist\public\"
)

:: Copy necessary configuration files
echo Copying configuration files...
copy /Y "interface.js" "dist\" 2>nul
copy /Y "package.json" "dist\" 2>nul
copy /Y "next.config.js" "dist\" 2>nul

:: Create environment files if they don't exist
if not exist ".env" (
    echo Creating default .env file...
    (
        echo API_KEY=123
        echo FRONTEND_URL=http://localhost:3000
        echo SMTP_SERVER=e2ksmtp01.e2k.ad.ge.com
        echo SMTP_SENDER=212724071@geaerospace.com
        echo ADMIN_EMAIL=212724071@geaerospace.com
        echo TEAM_EMAIL=team@example.com
        echo NODE_ENV=production
    ) > "dist\.env"
) else (
    copy /Y ".env" "dist\" 2>nul
)

if not exist ".env.local" (
    echo Creating default .env.local file...
    (
        echo NEXT_PUBLIC_API_URL=http://localhost:8000
        echo NEXT_PUBLIC_API_KEY=123
    ) > "dist\.env.local"
) else (
    copy /Y ".env.local" "dist\" 2>nul
)

:: Copy build manifest
if exist ".next\build-manifest.json" (
    echo Copying build manifest...
    copy /Y ".next\build-manifest.json" "dist\.next\" 2>nul
)

:: Install production dependencies in dist
cd dist
echo Installing production dependencies...
call npm install --omit=dev

:: Create the executable
echo Creating executable...
call pkg interface.js --targets node16-win-x64 --public-packages "*" -C GZip --output frontend.exe

if %ERRORLEVEL% neq 0 (
    echo Error: Failed to create executable
    cd ..
    exit /b 1
)

:: Create startup script
echo Creating startup script...
(
    echo @echo off
    echo setlocal EnableDelayedExpansion
    echo.
    echo :: Check if port 3000 is in use
    echo set PORT=3000
    echo netstat -ano ^| find ":%PORT% " ^| find "LISTENING" ^> nul
    echo if %%ERRORLEVEL%% equ 0 ^(
    echo     echo Port %%PORT%% is already in use. Stopping existing process...
    echo     for /f "tokens=5" %%%%a in ^('netstat -ano ^| find ":%PORT% " ^| find "LISTENING"'^) do ^(
    echo         taskkill /F /PID %%%%a
    echo         timeout /t 2 /nobreak ^>nul
    echo     ^)
    echo ^)
    echo.
    echo echo Starting CSV Upload Portal...
    echo start /B frontend.exe
    echo timeout /t 5 /nobreak
    echo start http://localhost:3000
    echo echo Application started! Browser will open automatically...
) > "start.bat"

cd ..

echo.
echo ===============================
echo Build completed successfully!
echo Executable and startup script created in dist folder
echo To start the application:
echo 1. Navigate to the dist folder
echo 2. Run start.bat
echo ===============================

exit /b 0