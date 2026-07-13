# ─────────────────────────────────────────────────────────────
#  app/database.py  —  Async SQLAlchemy engine + session factory
# ─────────────────────────────────────────────────────────────
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Generator

from config import settings

# ── Async Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,          # log SQL in dev
    pool_pre_ping=True,           # detect stale connections
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# ── Async Session factory ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ── Sync Engine ─────────────────────────────────────────────────────
sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# ── Sync Session factory ────────────────────────────────────────────
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Dependencies ────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an Async DB session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a Sync DB session and ensures cleanup."""
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
