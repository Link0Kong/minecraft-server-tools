@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYTHON=C:\Users\Ko_Li\AppData\Local\Programs\Python\Python312\pythonw.exe"
set "PORT=58888"
set "BASE_URL=http://localhost:%PORT%"

echo.
echo   ==================================================
echo     MC Dashboard v2.1 - Startup
echo   ==================================================
echo.

:: ---- Step 1: Check if a HEALTHY instance is already running ----
echo [1/4] Checking for existing healthy instance...
curl -s -o NUL --connect-timeout 3 "%BASE_URL%/api/status" 2>nul
if !errorlevel! equ 0 (
    echo   [OK] Dashboard already running and healthy ^(port %PORT%^)
    start "" http://localhost:%PORT%
    exit /b 0
)

:: ---- Step 2: Kill any stale/zombie processes on the port ----
echo [2/4] Cleaning up stale processes on port %PORT%...
set "FOUND_STALE=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%PORT%.*LISTENING"') do (
    echo   Killing PID %%a...
    taskkill /PID %%a /F 2>nul
    set "FOUND_STALE=1"
)
if "!FOUND_STALE!"=="1" (
    echo   [OK] Stale processes cleaned
    timeout /t 2 /nobreak >nul
) else (
    echo   [OK] Port is free
)

:: ---- Step 3: Verify Python runtime ----
echo [3/4] Verifying Python runtime...
if not exist "%PYTHON%" (
    echo   [WARN] pythonw not found at configured path
    echo         Looking up pythonw from PATH...
    for /f "delims=" %%p in ('where pythonw 2^>nul') do set "PYTHON=%%p"
    if "!PYTHON!"=="" (
        echo   [ERROR] pythonw.exe not found anywhere!
        echo          Please install Python or update PYTHON path in this script.
        pause
        exit /b 1
    )
    echo   [OK] Found: !PYTHON!
) else (
    echo   [OK] Python: %PYTHON%
)

:: ---- Step 4: Start the server ----
echo [4/4] Starting dashboard server...
start "" "%PYTHON%" "%~dp0mc_dashboard.py"

:: Wait for it to come up
echo   Waiting for startup...
set /a COUNT=0
:waitloop
timeout /t 2 /nobreak >nul
set /a COUNT+=1
curl -s -o NUL --connect-timeout 2 "%BASE_URL%/api/status" 2>nul
if !errorlevel! equ 0 (
    echo.
    echo   ==================================================
    echo     [SUCCESS] Dashboard is ready!
    echo     Opening http://localhost:%PORT%
    echo   ==================================================
    start "" http://localhost:%PORT%
    exit /b 0
)
if !COUNT! lss 15 goto waitloop

:: Timeout - something went wrong
echo.
echo   ==================================================
echo     [WARNING] Server process started but not
echo     responding after 30 seconds.
echo.
echo     Try running manually to see errors:
echo       python mc_dashboard.py
echo   ==================================================
pause
exit /b 0
