@echo off
setlocal

title NovelForge AI

echo.
echo  ============================================
echo   NovelForge AI - Local Light Novel Writer
echo  ============================================
echo.

set "BACKEND_DIR=%~dp0backend"
set "PORT=8000"
set "REQ_FILE=%~dp0requirements.txt"
set "PYTHON_EXE="

REM --- Detect Python (py launcher first, then python) ---
py --version >nul 2>&1
if not errorlevel 1 set "PYTHON_EXE=py"

if "%PYTHON_EXE%"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    echo  [ERROR] Python not found.
    echo  Install Python 3.11+ from: https://www.python.org/downloads/
    echo  Check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  [OK] Python: %PYTHON_EXE%
echo.

REM --- Install dependencies only if fastapi is missing ---
echo  [1/3] Checking dependencies...
%PYTHON_EXE% -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo  [..] First run - installing packages...
    %PYTHON_EXE% -m pip install -r "%REQ_FILE%" -q
    echo  [OK] Packages installed.
) else (
    echo  [OK] Dependencies ready.
)
echo.

REM --- Check backend exists ---
if not exist "%BACKEND_DIR%\main.py" (
    echo  [ERROR] Not found: %BACKEND_DIR%\main.py
    pause
    exit /b 1
)

REM --- Start server (using /d flag to set working directory) ---
echo  [2/3] Starting backend server...
start "NovelForge-Backend" /min /d "%BACKEND_DIR%" %PYTHON_EXE% -m uvicorn main:app --host 127.0.0.1 --port %PORT%

REM --- Poll until server responds ---
echo  [3/3] Waiting for server...
set "TRIES=0"

:poll
timeout /t 2 /nobreak >nul
%PYTHON_EXE% -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%PORT%/api/health',timeout=1)" >nul 2>&1
if not errorlevel 1 goto :ready
set /a TRIES+=1
if %TRIES% LSS 15 goto :poll
echo  [WARN] Server is slow to start. Opening browser anyway...
goto :open

:ready
echo  [OK] Server is up!

:open
echo.
echo  ============================================
echo   URL: http://127.0.0.1:%PORT%
echo  ============================================
echo.
start "" "http://127.0.0.1:%PORT%"
echo  Server runs in the minimized NovelForge-Backend window.
echo  Press any key to close this launcher.
echo.
pause >nul
