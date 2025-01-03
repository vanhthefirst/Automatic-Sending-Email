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
xcopy /E /I /Y ".next\standalone\*" "dist\"
xcopy /E /I /Y ".next\static\*" "dist\.next\static\"
if exist "public" xcopy /E /I /Y "public\*" "dist\public\"
copy /Y "interface.js" "dist\"
copy /Y "package.json" "dist\"
copy /Y ".env" "dist\"
copy /Y ".env.local" "dist\"

:: Install production dependencies in dist
cd dist
echo Installing production dependencies...
call npm install --omit=dev
cd ..

:: Create the executable
echo Creating executable...
cd dist
call pkg interface.js --targets node16-win-x64 --public-packages "*" -C GZip --no-native-build

if %ERRORLEVEL% neq 0 (
    echo Error: Failed to create executable
    cd ..
    exit /b 1
)

:: Rename the executable
if exist "interface.exe" (
    rename "interface.exe" "frontend.exe"
)

cd ..

echo.
echo ===============================
echo Build completed successfully!
echo Executable created at: dist\frontend.exe
echo ===============================

exit /b 0