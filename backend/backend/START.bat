@echo off
title VendorClear AI — Backend Server
color 0F
echo.
echo  ==========================================
echo   VendorClear AI — Starting Backend Server
echo  ==========================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Install / upgrade dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt -q --break-system-packages 2>nul || pip install -r requirements.txt -q
echo       Done.

:: Create logs folder if missing
if not exist logs mkdir logs

:: Check .env exists
if not exist .env (
    echo [2/3] Creating .env from example...
    copy .env.example .env >nul
    echo       Done.  ^(edit .env to add MySQL or Gemini key later^)
) else (
    echo [2/3] .env found.
)

echo.
echo [3/3] Starting VendorClear AI on http://localhost:8000
echo.
echo  API docs: http://localhost:8000/api/docs
echo  Health:   http://localhost:8000/api/health
echo.
echo  Open vendorclear-app.html in your browser, then register and sign in.
echo  Press Ctrl+C to stop the server.
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
