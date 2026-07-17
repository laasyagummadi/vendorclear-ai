# ================================================================
#  VendorClear AI - single-container deployment
#  Stage 1 builds the React frontend; stage 2 runs the FastAPI
#  backend, which also serves the built frontend (see main.py).
# ================================================================

# --- Stage 1: build the frontend --------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend + built frontend --------------------------
FROM python:3.12-slim
WORKDIR /app

# System deps kept minimal; pdfplumber/Pillow wheels cover most needs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/dist ./frontend/dist

WORKDIR /app/backend

# Sensible production defaults; override any of these in your host's
# environment settings. SECRET_KEY *must* be overridden in production.
ENV APP_ENV=production \
    DEBUG=false \
    USE_SQLITE=true \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD curl -sf http://localhost:8000/api/health || exit 1

# Seed demo data (idempotent - skips anything that already exists),
# then start the server. $PORT is provided by most hosts; default 8000.
CMD ["sh", "-c", "python -m scripts.seed_data && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
