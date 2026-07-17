# ─────────────────────────────────────────────────────────────
#  app/database.py  —  Async SQLAlchemy engine + session factory
#
#  Set USE_SQLITE=true in .env for zero-config local dev mode.
#  No MySQL needed — uses a local vendorclear.db file.
# ─────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from config import settings

# ── Engine ────────────────────────────────────────────────────
# settings.database_url resolves in priority order:
#   DATABASE_URL env var (hosted deployments) > USE_SQLITE > DB_* (MySQL)
_url = settings.database_url

if _url.startswith("sqlite"):
    engine = create_async_engine(
        _url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        _url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )

# ── Session factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Dependency ────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a DB session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
