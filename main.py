# ─────────────────────────────────────────────────────────────
#  main.py  —  VendorClear AI FastAPI application entry point
# ─────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from loguru import logger
import sys

from config import settings
from app.database import engine
from app.models.base import Base
from app.routes import auth, vendors
from app.middleware.logging import RequestLoggingMiddleware
from app.utils.exceptions import register_exception_handlers

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
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.app_name} starting — env={settings.app_env}")
    # In development you can auto-create tables; in production use Alembic
    if settings.app_env == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✓ Database tables verified")
    yield
    logger.info("⏹  Shutting down...")
    await engine.dispose()


# ── App factory ───────────────────────────────────────────────
app = FastAPI(
    title=f"{settings.app_name} API",
    description="AI-powered Vendor Compliance & Intelligence Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ── Exception handlers ────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(vendors.router, prefix=settings.api_v1_prefix)


# ── Root & health ─────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "1.0.0",
    }
