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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from app.database import engine, AsyncSessionLocal
from app.models.base import Base
from app.routes import auth, vendors, documents, analysis, dashboard, alerts, config, policies, audit, scoring_policies
from app.middleware.logging import RequestLoggingMiddleware
from app.utils.exceptions import register_exception_handlers
from app.utils.rate_limit import limiter
from app.models.notification_log import NotificationTrigger
from app.services.notification_service import NotificationService

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


# ── Lifespan ───────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.app_name} starting — env={settings.app_env}")
    # create_all is idempotent: it only creates tables that don't exist.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")

    from app.database import AsyncSessionLocal
    
    # 1. Seed Version Configurations
    from app.services.config_service import ConfigService
    async with AsyncSessionLocal() as _db:
        await ConfigService(_db).ensure_seeded()
        logger.info("Version configurations seeded")

    # 2. Seed Compliance Scoring Policies
    from app.repositories.policy_repository import PolicyRepository
    async with AsyncSessionLocal() as session:
        created = await PolicyRepository(session).seed_defaults_if_missing()
        await session.commit()
        if created:
            logger.info(f"Seeded {len(created)} default compliance policy(ies)")

    # 3. Daily vendor alert-email job
    scheduler = AsyncIOScheduler()

    async def _send_daily_vendor_alerts():
        async with AsyncSessionLocal() as session:
            try:
                result = await NotificationService(session).run(
                    trigger=NotificationTrigger.SCHEDULED,
                    expiry_days=settings.alert_expiry_lookahead_days,
                )
                logger.info(f"Daily vendor alert email job finished: {result}")
            except Exception:
                logger.exception("Daily vendor alert email job failed")

    scheduler.add_job(
        _send_daily_vendor_alerts,
        "cron",
        hour=settings.alert_schedule_hour,
        minute=0,
        id="daily_vendor_alerts",
        replace_existing=True,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info(
        f"Vendor alert scheduler started — runs daily at {settings.alert_schedule_hour:02d}:00 "
        f"(emails {'enabled' if settings.alerts_email_enabled else 'disabled — set ALERTS_EMAIL_ENABLED=true'})"
    )

    yield
    logger.info("Shutting down...")
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
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
if settings.use_sqlite or settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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
app.include_router(policies.router, prefix=settings.api_v1_prefix)
app.include_router(config.router, prefix=settings.api_v1_prefix)
app.include_router(audit.router, prefix=settings.api_v1_prefix)
app.include_router(scoring_policies.router, prefix=settings.api_v1_prefix)


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
        candidate = _os.path.normpath(_os.path.join(_FRONTEND_DIST, full_path))
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
