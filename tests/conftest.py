# ─────────────────────────────────────────────────────────────
#  tests/conftest.py  —  pytest fixtures for VendorClear AI
# ─────────────────────────────────────────────────────────────
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from main import app
from app.database import get_db
from app.models.base import Base

# ── File-based SQLite for tests (shares state between sync & async) ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sync_test_engine = create_engine(
    "sqlite:///test.db",
    connect_args={"check_same_thread": False},
)
SyncTestSessionLocal = sessionmaker(
    bind=sync_test_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Override DB dependencies ──────────────────────────────────
async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def override_get_sync_db():
    db = SyncTestSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


from app.database import get_sync_db
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_sync_db] = override_get_sync_db


# ── Session-scoped fixtures ───────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    import os
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except Exception:
            pass

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except Exception:
            pass


@pytest_asyncio.fixture(autouse=True)
async def clean_database_tables():
    """Clean all tables between individual tests to ensure isolated environments."""
    from sqlalchemy import text
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM findings"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM documents"))
        await conn.execute(text("DELETE FROM vendors"))
        await conn.execute(text("DELETE FROM users"))


@pytest_asyncio.fixture
async def db_session():
    """Fresh DB session for each test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Convenience fixtures ──────────────────────────────────────
@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register a test user and return the response body."""
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "test@vendorclear.ai",
        "password": "Secure123",
        "confirm_password": "Secure123",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user) -> dict:
    """Log in and return Authorization headers."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@vendorclear.ai",
        "password": "Secure123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
