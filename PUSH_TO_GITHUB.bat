@echo off
echo.
echo  VendorClear AI — Push Backend to GitHub
echo  -----------------------------------------
echo.

cd /d "%~dp0"
echo  Working folder: %CD%
echo.

echo  [1/4] Initializing git...
git init
git checkout -b main 2>nul || git branch -M main

echo  [2/4] Staging all files...
git add .
git status --short

echo.
echo  [3/4] Committing...
git commit -m "feat: FastAPI backend — Laasya's foundation layer

- FastAPI + async SQLAlchemy 2.0 + MySQL (aiomysql)
- Alembic migrations configured
- User model + JWT auth (register, login, refresh, change-password)
- Vendor model with status/risk enums, diversity types, insurance dates
- Repository pattern: UserRepository + VendorRepository
- Controller layer: AuthController + VendorController
- API routes: /api/v1/auth/* and /api/v1/vendors/*
- Request logging middleware + custom exception handlers
- Rate limiting (slowapi), bcrypt password hashing
- pytest test suite: 28 test cases (SQLite in-memory)"

echo.
echo  [4/4] Pushing to GitHub...
echo  When prompted: username = laasyagummadi
echo  Password = your GitHub Personal Access Token
echo  (Get one at: github.com/settings/tokens → repo scope)
echo.

git remote remove origin 2>nul
git remote add origin https://github.com/laasyagummadi/vendorclear-ai.git
git push -u origin main

echo.
echo  ✓ Done! Visit: https://github.com/laasyagummadi/vendorclear-ai
pause
