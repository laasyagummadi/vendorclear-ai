# VendorClear AI — Vendor Intelligence Platform

> AI-powered vendor compliance and vendor intelligence platform.
> Built with **FastAPI + SQLAlchemy** (backend) and **React + Vite** (frontend).

---

## ⚡ Quick Start (do this first)

**Do not open any `.html` file directly in your browser.** This app has a real backend and frontend that both need to be running — opening a file from your Downloads/Desktop folder will always show "Cannot reach backend," because no server is running yet.

### Windows
Double-click **`START-windows.bat`** in this folder. It installs everything it needs (Python packages, Node packages) the first time, seeds demo data, starts both servers, and opens your browser automatically. Leave the two black terminal windows it opens running while you use the app.

### Mac / Linux
```bash
./START-mac-linux.sh
```
Same thing — first run installs dependencies and seeds demo data, then starts both servers and opens your browser.

### Either way, once it's running:
- App: **http://localhost:3000**
- API docs: **http://localhost:8000/api/docs**
- Demo login: **demo@vendorclear.ai** / **DemoPass123** — or just click **Register** to create your own account (it's saved for real, in the database, immediately)

If port 3000 or 8000 is already in use by something else on your machine, stop that other program first, or edit the port in `frontend/vite.config.js` and `backend/.env`.

---

## Project Overview

VendorClear AI automates the analysis of Certificates of Insurance (COI) and Vendor Diversity Certificates. It extracts structured data from uploaded documents, applies rule-based compliance validation, calculates risk scores, and provides dashboards and alerts for procurement and compliance teams.

**Core capabilities:**
- AI-assisted document analysis (COI, diversity certificates) — uses Google Gemini if you provide an API key, otherwise falls back to a built-in regex extractor so the app works out of the box with no external account needed
- Insurance verification against configurable coverage thresholds
- Vendor diversity certification tracking (MBE, WBE, DBE, SBE, VOSB, HUBZone)
- Risk scoring engine (0–100, tiered Low / Medium / High)
- Proactive expiry alerts
- Compliance trend analytics and reports

> **Not yet implemented:** a natural-language chat assistant has been discussed but does not exist in this codebase yet (no route, no UI). Everything else on this list is real and tested.

---

## Architecture

```
Browser (React SPA, port 3000)
       │  HTTP/JSON  (Vite dev proxy → :8000 in dev; same-origin in prod)
       ▼
FastAPI (Python, port 8000)
  ├─ SQLAlchemy (async) → SQLite (dev, zero-config) or MySQL (production)
  ├─ JWT auth (python-jose + bcrypt)
  ├─ Gemini AI or regex fallback → document extraction
  ├─ Compliance rules engine → risk scoring
  └─ slowapi → rate limiting on auth/upload endpoints
```

## Folder Structure

```
vendorclear-ai/
├── START-windows.bat        # one-click launcher (Windows)
├── START-mac-linux.sh       # one-click launcher (Mac/Linux)
├── backend/                 # FastAPI app
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── routes/          # API endpoints
│   │   ├── controllers/     # request handling / orchestration
│   │   ├── services/        # Gemini, OCR, compliance engine
│   │   ├── repositories/    # DB queries
│   │   └── schemas/         # Pydantic request/response models
│   ├── scripts/seed_data.py # demo data
│   ├── alembic/              # DB migrations
│   └── tests/                # pytest suite (74 tests)
└── frontend/                 # React + Vite app
    └── src/
        ├── components/       # pages + modals
        ├── api.js            # fetch wrapper
        └── test/              # vitest suite (34 tests)
```

---

## Manual Setup (if you'd rather not use the START script)

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate.bat
pip install -r requirements.txt
cp .env.example .env            # already defaults to SQLite, no MySQL needed
python -m scripts.seed_data     # optional: adds 10 demo vendors + a demo login
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Then open **http://localhost:3000**.

### Running the test suites
```bash
cd backend && pytest              # 74 tests
cd frontend && npm test           # 34 tests
```

---

## 🚀 Deploying to the Internet

The repo ships with a **Dockerfile** that builds the frontend and serves the whole app (frontend + API) as **one service** — no CORS setup, one URL. It works on any Docker host; the easiest free option is Render:

### Deploy to Render (free tier)
1. Push this folder to a GitHub repository (it already includes `render.yaml`).
2. Go to [render.com](https://render.com) → **New → Blueprint** → connect your repo.
3. Render reads `render.yaml`, builds the Docker image, generates a `SECRET_KEY`, and deploys.
4. Your app is live at `https://<your-service>.onrender.com` — registration, login, vendors, uploads, everything.

**Data persistence note:** the default deploy uses SQLite on the container's disk, which is **wiped whenever the service redeploys or restarts** (fine for demos). For permanent data, create a free Postgres database (e.g. [Neon](https://neon.tech) or Render's own Postgres) and set its connection string as a `DATABASE_URL` environment variable in the Render dashboard — the app detects it automatically and uses it instead of SQLite. Tables are created on first startup; no manual migration step needed.

### Deploy anywhere else (Railway, Fly.io, a VPS…)
```bash
docker build -t vendorclear-ai .
docker run -p 8000:8000 -e SECRET_KEY=$(openssl rand -hex 32) vendorclear-ai
```
Then open port 8000. Set `DATABASE_URL` for a hosted database, same as above.

### Production checklist
- `SECRET_KEY` — must be a strong random value (Render's blueprint generates one automatically)
- `APP_ENV=production` and `DEBUG=false` (the Dockerfile defaults to these)
- `DATABASE_URL` — set it if you need data to survive restarts
- CORS: not needed in this setup — frontend and API share one origin

---

## Environment Variables (`backend/.env`)

```env
APP_ENV=development
USE_SQLITE=true                 # zero-config local dev; set false + fill in DB_* for MySQL
SECRET_KEY=change-me-to-a-random-secret-before-going-live
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_ORIGINS=["http://localhost:3000"]
RATE_LIMIT_PER_MINUTE=100
GEMINI_API_KEY=                 # optional — leave blank to use the built-in extractor
```

For production: set `USE_SQLITE=false`, fill in `DB_HOST`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` for your MySQL instance, then run `alembic upgrade head` in `backend/` to create the schema.

---

## API Reference

| Method | Endpoint                                   | Description                    |
|--------|---------------------------------------------|---------------------------------|
| POST   | `/api/v1/auth/register`                     | Create an account               |
| POST   | `/api/v1/auth/login`                        | Get access + refresh tokens     |
| GET    | `/api/v1/auth/me`                           | Current user profile            |
| GET    | `/api/v1/vendors`                           | List vendors (paginated, filterable) |
| POST   | `/api/v1/vendors`                           | Create a vendor                 |
| GET    | `/api/v1/vendors/{id}`                      | Vendor detail                   |
| PATCH  | `/api/v1/vendors/{id}`                      | Update a vendor                 |
| POST   | `/api/v1/vendors/{id}/documents`            | Upload + analyze a document     |
| GET    | `/api/v1/analyses/{id}`                     | Analysis result + findings      |
| GET    | `/api/v1/dashboard/summary`                 | Dashboard stats                 |
| GET    | `/api/v1/dashboard/compliance-report`       | Full compliance report          |
| GET    | `/api/v1/alerts`                            | Expiry + compliance alerts      |

Full interactive docs (try requests live): **http://localhost:8000/api/docs**

---

## Compliance Rules

| Rule                    | Severity | Trigger                                   |
|--------------------------|----------|---------------------------------------------|
| MISSING_GL_LIMIT         | —        | No General Liability limit found            |
| LOW_GL_LIMIT              | —        | GL below the configured threshold           |
| DOCUMENT_EXPIRED          | CRITICAL | Expiry date is in the past                   |
| MISSING_EXPIRY_DATE       | HIGH     | No expiry date found                        |
| MISSING_OWNERSHIP_PERCENT | HIGH     | Diversity cert missing ownership %          |
| LOW_OWNERSHIP_PERCENT     | HIGH     | Ownership below 51%                          |
| LOW_CONFIDENCE            | MEDIUM   | Extraction confidence below 70%              |

**Status mapping:** any CRITICAL finding → `NON_COMPLIANT`; any HIGH finding or score < 70 → `NEEDS_REVIEW`; otherwise → `COMPLIANT`.

---

## Tech Stack

| Layer      | Technology                                       |
|------------|---------------------------------------------------|
| Frontend   | React 18, Vite, Chart.js                          |
| Backend    | Python 3.11+, FastAPI, SQLAlchemy (async)          |
| Database   | SQLite (dev) / MySQL (production)                  |
| AI         | Google Gemini (optional) with regex fallback       |
| Auth       | JWT (python-jose), bcrypt                          |
| Security   | CORS, slowapi rate limiting, file upload sandboxing|
| Testing    | pytest (backend, 74 tests), Vitest + RTL (frontend, 34 tests) |

---

*© 2026 VendorClear AI — Vendor Intelligence, Clarity Assured.*
