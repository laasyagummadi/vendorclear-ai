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
from app.routes import documents, analysis, dashboard, alerts
from app.middleware.logging import RequestLoggingMiddleware
from app.utils.exceptions import register_exception_handlers

logger.remove()
logger.add(sys.stdout, level="DEBUG" if settings.debug else "INFO", colorize=True)
logger.add("logs/vendorclear.log", rotation="10 MB", level="INFO")

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"VendorClear AI starting")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")
    yield
    await engine.dispose()

app = FastAPI(title="VendorClear AI API", version="1.0.0", docs_url="/api/docs", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(vendors.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(analysis.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(alerts.router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root():
    return {"service": "VendorClear AI", "version": "1.0.0", "docs": "/api/docs"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
