# ─────────────────────────────────────────────────────────────
#  tests/conftest.py  —  pytest fixtures for VendorClear AI
# ─────────────────────────────────────────────────────────────
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Importing main triggers the full app import chain:
# main → routes → controllers → models (all registered with Base.metadata)
from main import app
from app.database import get_db
from app.models.base import Base

# ── In-memory SQLite for tests (no MySQL needed) ──────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Override DB dependency ────────────────────────────────────
async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


import sys; print("DEBUG app:", type(app), id(app)); print("DEBUG sys.modules app:", type(sys.modules.get("app"))); app.dependency_overrides[get_db] = override_get_db


# ── Session-scoped fixtures ───────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


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
    return {"