@echo off
cd /d "%~dp0"

echo ================================================
echo   VendorClear AI - First-time setup and launch
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 goto :nopython
where node >nul 2>nul
if errorlevel 1 goto :nonode
goto :prereqsok

:nopython
echo [ERROR] Python was not found on your PATH.
echo Install Python 3.11 or newer from https://python.org/downloads then run this again.
pause
exit /b 1

:nonode
echo [ERROR] Node.js was not found on your PATH.
echo Install Node.js 18 or newer from https://nodejs.org then run this again.
pause
exit /b 1

:prereqsok
cd backend

if exist venv goto :venvdone
echo [1/5] Creating Python virtual environment...
python -m venv venv
:venvdone

echo [2/5] Installing backend dependencies - first run only, about a minute...
call venv\Scripts\activate.bat
pip install -r requirements.txt --disable-pip-version-check

echo Verifying installation...
python -c "import greenlet, sqlalchemy, fastapi, uvicorn, jose, bcrypt, aiosqlite, pydantic" 
if errorlevel 1 goto :importfail
goto :importok

:importfail
echo.
echo [ERROR] A required Python package failed to install correctly.
echo The missing package is named in the error message just above this line.
echo Try running this script again - if it fails the same way twice,
echo send a screenshot of THIS window.
pause
exit /b 1

:importok
echo All backend packages verified.

if exist .env goto :envdone
echo Creating backend .env from the template - SQLite mode, no MySQL needed.
copy .env.example .env >nul
:envdone

if exist vendorclear.db goto :dbexists
echo [3/5] Seeding demo data - 10 sample vendors and a demo login.
python -m scripts.seed_data
goto :dbdone
:dbexists
echo [3/5] Database already exists, skipping seed.
:dbdone

echo Starting backend on http://localhost:8000 ...
start "VendorClear Backend - keep this window open" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

cd ..\frontend

if exist node_modules goto :fedone
echo [4/5] Installing frontend dependencies - first run only, about a minute...
call npm install
:fedone

echo [5/5] Starting frontend on http://localhost:3000 ...
start "VendorClear Frontend - keep this window open" cmd /k "npm run dev"

echo.
echo Waiting for both servers to finish starting...
timeout /t 8 /nobreak > nul

start http://localhost:3000

echo.
echo ================================================
echo   VendorClear AI is running
echo ================================================
echo   App:      http://localhost:3000
echo   API docs: http://localhost:8000/api/docs
echo.
echo   Demo login:  demo@vendorclear.ai  /  DemoPass123
echo   or click Register to create your own account.
echo.
echo   Two new windows opened for the backend and frontend
echo   servers - leave them running. Close them, or press
echo   Ctrl+C in each, to stop the app.
echo ================================================
pause
