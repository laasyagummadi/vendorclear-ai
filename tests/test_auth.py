# ─────────────────────────────────────────────────────────────
#  tests/test_auth.py  —  Authentication endpoint tests
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Alice Smith",
            "email": "alice@test.com",
            "password": "Secure123",
            "confirm_password": "Secure123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["email"] == "alice@test.com"
        assert body["user"]["full_name"] == "Alice Smith"
        assert "hashed_password" not in body

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "full_name": "Bob Jones",
            "email": "duplicate@test.com",
            "password": "Secure123",
            "confirm_password": "Secure123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]

    async def test_register_password_mismatch(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Carol White",
            "email": "carol@test.com",
            "password": "Secure123",
            "confirm_password": "Different1",
        })
        assert resp.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Dave Brown",
            "email": "dave@test.com",
            "password": "weak",
            "confirm_password": "weak",
        })
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Eve Green",
            "email": "not-an-email",
            "password": "Secure123",
            "confirm_password": "Secure123",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@vendorclear.ai",
            "password": "Secure123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@vendorclear.ai",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "Secure123",
        })
        assert resp.status_code == 401


class TestTokenRefresh:
    async def test_refresh_success(self, client: AsyncClient, registered_user):
        login = await client.post("/api/v1/auth/login", json={
            "email": "test@vendorclear.ai",
            "password": "Secure123",
        })
        refresh_token = login.json()["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        assert resp.status_code == 401


class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "test@vendorclear.ai"
        assert "hashed_password" not in body

    async def test_get_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403  # HTTPBearer returns 403 when no token
