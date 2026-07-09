# tests/conftest.py  -  pytest fixtures for VendorClear AI
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from main import app
from app.database import get_db
from app.models.base import Base

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


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


# ---- Session-scoped DB setup ----------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


# ---- Session-scoped HTTP client (shared across all tests) ------------
@pytest_asyncio.fixture(scope="session")
async def session_client(setup_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---- Function-scoped client for isolation ----------------------------
@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---- Register once per session, reuse across tests -------------------
@pytest_asyncio.fixture(scope="session")
async def registered_user(session_client):
    resp = await session_client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "test@vendorclear.ai",
        "password": "Secure123",
        "confirm_password": "Secure123",
    })
    # 201 on first run, 409 if already exists (re-run) - both are OK
    assert resp.status_code in (201, 409)
    return resp.json()


@pytest_asyncio.fixture(scope="session")
async def auth_headers(session_client, registered_user):
    resp = await session_client.post("/api/v1/auth/login", json={
        "email": "test@vendorclear.ai",
        "password": "Secure123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": "Bearer " + token}
