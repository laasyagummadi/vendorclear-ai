# ─────────────────────────────────────────────────────────────
#  main.py  —  VendorClear AI FastAPI application entry point
# ─────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from loguru import logger
import sys

from config import settings
from app.database import engine
from app.models.base import Base
from app.routes import auth, vendors
from app.routes import documents, analysis, dashboard, alerts
from app.middleware.logging import RequestLoggingMiddleware
from app.utils.exceptions import register_exception_handlers
from app.utils.rate_limit import limiter

# ── Loguru configuration ──────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.debug else "INFO",
    colorize=True,
)
logger.add(
    "logs/vendorclear.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="INFO",
)

# ── Rate limiter ──────────────────────────────────────────────
# (instance now lives in app.utils.rate_limit so route files can use it too)


# ── Lifespan ───────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.app_name} starting — env={settings.app_env}")
    # create_all is idempotent: it only creates tables that don't exist.
    # This makes a fresh deployment (SQLite file or a brand-new hosted
    # Postgres/MySQL via DATABASE_URL) work with zero manual steps.
    # Schema *changes* on an existing production DB still go through
    # Alembic migrations (alembic upgrade head).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")
    yield
    logger.info("Shutting down...")
    await engine.dispose()


# ── App factory ────────────────────────────────────────────────
app = FastAPI(
    title=f"{settings.app_name} API",
    description="AI-powered Vendor Compliance & Intelligence Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
# Dev/SQLite mode: allow all origins for zero-friction local development.
# Production: restrict to the explicit allow-list from settings.allowed_origins.
# NOTE: previously this was hardcoded to allow_origins=["*"] unconditionally,
# which silently ignored settings.allowed_origins even in production. Fixed here.
if settings.use_sqlite or settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,   # must be False when allow_origins=["*"]
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Middleware ──────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(vendors.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(analysis.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(alerts.router, prefix=settings.api_v1_prefix)


# ── Health ────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "1.0.0",
    }


# ── Frontend (production single-service deployment) ──────────
# If the React app has been built (frontend/dist exists, or the
# FRONTEND_DIST env var points at a build), serve it directly from
# this process: one deployable service, same-origin API, no CORS
# issues. In local dev (Vite on :3000) dist doesn't exist and the
# plain JSON root below is used instead.
import os as _os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_FRONTEND_DIST = _os.environ.get(
    "FRONTEND_DIST",
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "frontend", "dist"),
)

if _os.path.isdir(_FRONTEND_DIST):
    _assets = _os.path.join(_FRONTEND_DIST, "assets")
    if _os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        """Serve the built SPA; unknown paths fall back to index.html
        so client-side navigation and refreshes work."""
        candidate = _os.path.normpath(_os.path.join(_FRONTEND_DIST, full_path))
        # stay inside dist/ (defense against ../ traversal in the URL path)
        if candidate.startswith(_os.path.normpath(_FRONTEND_DIST)) and _os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_os.path.join(_FRONTEND_DIST, "index.html"))
else:
    @app.get("/", tags=["root"])
    async def root():
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "docs": "/api/docs",
            "mode": "SQLite dev" if settings.use_sqlite else "MySQL production",
        }
