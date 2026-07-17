#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "================================================"
echo "  VendorClear AI - First-time setup + launch"
echo "================================================"
echo

command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found. Install Python 3.11+ first."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "[ERROR] node not found. Install Node.js 18+ first."; exit 1; }

cd backend

if [ ! -d venv ]; then
  echo "[1/5] Creating Python virtual environment..."
  python3 -m venv venv
fi

echo "[2/5] Installing backend dependencies (first run only, ~1 min)..."
source venv/bin/activate
pip install -r requirements.txt --disable-pip-version-check

echo "Verifying installation..."
if ! python -c "import greenlet, sqlalchemy, fastapi, uvicorn, jose, bcrypt, aiosqlite, pydantic"; then
  echo "[ERROR] A required Python package failed to install correctly."
  echo "The missing package is named in the error message just above this line."
  exit 1
fi
echo "All backend packages verified."

if [ ! -f .env ]; then
  echo "Creating backend/.env from the template (SQLite mode, no MySQL needed)..."
  cp .env.example .env
fi

if [ ! -f vendorclear.db ]; then
  echo "[3/5] Seeding demo data (10 sample vendors + a demo login)..."
  python -m scripts.seed_data
else
  echo "[3/5] Database already exists, skipping seed."
fi

echo "Starting backend on http://localhost:8000 ..."
(python -m uvicorn main:app --host 127.0.0.1 --port 8000 > ../backend.log 2>&1 &)

cd ../frontend

if [ ! -d node_modules ]; then
  echo "[4/5] Installing frontend dependencies (first run only, ~1 min)..."
  npm install
fi

echo "[5/5] Starting frontend on http://localhost:3000 ..."
(npm run dev > ../frontend.log 2>&1 &)

echo
echo "Waiting for both servers to finish starting..."
sleep 8

if command -v open >/dev/null 2>&1; then open http://localhost:3000
elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:3000
fi

echo
echo "================================================"
echo "  VendorClear AI is running"
echo "================================================"
echo "  App:      http://localhost:3000"
echo "  API docs: http://localhost:8000/api/docs"
echo
echo "  Demo login:  demo@vendorclear.ai / DemoPass123"
echo "  (or click Register to create your own account)"
echo
echo "  Logs: backend.log and frontend.log in this folder."
echo "  To stop: close this terminal or run"
echo "    pkill -f 'uvicorn main:app' && pkill -f 'vite'"
echo "================================================"
