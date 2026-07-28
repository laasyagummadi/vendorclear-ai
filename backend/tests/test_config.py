# ─────────────────────────────────────────────────────────────
#  tests/test_config.py  —  Version-config admin feature tests
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _make_admin(db_session, email="admin-cfg@example.com"):
    """Create (or promote) an ADMIN user and return login-ready credentials."""
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    existing = (await db_session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        existing.role = UserRole.ADMIN
        existing.is_admin = True
        db_session.add(existing)
    else:
        db_session.add(User(
            email=email, full_name="Config Admin",
            hashed_password=hash_password("AdminPass123"),
            is_admin=True, role=UserRole.ADMIN,
        ))
    await db_session.commit()
    return email, "AdminPass123"


_ADMIN_TOKEN_CACHE = {}


async def _admin_headers(client: AsyncClient, db_session):
    # Cache the token across tests in this module: logging in for every test
    # trips the 10/min login rate limit once this module runs alongside the
    # rest of the suite (the rate limiter is working as intended).
    if "token" not in _ADMIN_TOKEN_CACHE:
        email, pw = await _make_admin(db_session)
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert resp.status_code == 200, resp.text
        _ADMIN_TOKEN_CACHE["token"] = resp.json()["access_token"]
    return {"Authorization": "Bearer " + _ADMIN_TOKEN_CACHE["token"]}


class TestVersionConfigRead:
    async def test_admin_reads_both_version_defaults(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/config/versions", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # requirement 1: V1 = ₹5,00,000, V2 = ₹10,00,000
        assert body["version_1"]["compliance_compensation_inr"] == 500000
        assert body["version_2"]["compliance_compensation_inr"] == 1000000

    async def test_config_exposes_schema_for_ui(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        body = (await client.get("/api/v1/config/versions", headers=headers)).json()
        assert "schema" in body
        assert "compliance_compensation_inr" in body["schema"]


class TestAdminOnlyAccess:
    async def test_vendor_cannot_read_config(self, client: AsyncClient, vendor_auth_headers):
        # vendor_auth_headers is a default VENDOR-role user
        resp = await client.get("/api/v1/config/versions", headers=vendor_auth_headers)
        assert resp.status_code == 403

    async def test_vendor_cannot_update_config(self, client: AsyncClient, vendor_auth_headers):
        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"compliance_compensation_inr": 999}, "apply_to_existing": False},
            headers=vendor_auth_headers,
        )
        assert resp.status_code == 403

    async def test_unauthenticated_blocked(self, client: AsyncClient):
        assert (await client.get("/api/v1/config/versions")).status_code == 403


class TestApplyToExisting:
    """Requirement 5 — the apply-to-existing checkbox behavior."""

    async def _make_v1_vendor(self, client, headers):
        v = (await client.post("/api/v1/vendors", json={"name": "Apply Test Vendor"}, headers=headers)).json()
        # assign to version 1 (snapshots current v1 config onto the vendor)
        await client.put(
            f"/api/v1/config/vendors/{v['id']}/version",
            json={"version": 1}, headers=headers,
        )
        return v["id"]

    async def test_unchecked_preserves_existing_vendor(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        vid = await self._make_v1_vendor(client, headers)
        before = (await client.get(f"/api/v1/config/vendors/{vid}/effective", headers=headers)).json()
        base = before["effective_config"]["compliance_compensation_inr"]

        # update V1 config WITHOUT applying to existing
        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"compliance_compensation_inr": base + 111}, "apply_to_existing": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["vendors_updated"] == 0

        after = (await client.get(f"/api/v1/config/vendors/{vid}/effective", headers=headers)).json()
        # existing vendor keeps its old snapshot
        assert after["effective_config"]["compliance_compensation_inr"] == base

    async def test_checked_updates_existing_vendor(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        vid = await self._make_v1_vendor(client, headers)
        target = 654321

        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"compliance_compensation_inr": target}, "apply_to_existing": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["vendors_updated"] >= 1

        after = (await client.get(f"/api/v1/config/vendors/{vid}/effective", headers=headers)).json()
        assert after["effective_config"]["compliance_compensation_inr"] == target


class TestVersionAssignment:
    async def test_assign_vendor_to_v2_snapshots_v2_config(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        v = (await client.post("/api/v1/vendors", json={"name": "V2 Assign Test"}, headers=headers)).json()
        resp = await client.put(
            f"/api/v1/config/vendors/{v['id']}/version",
            json={"version": 2}, headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assigned_version"] == 2
        # snapshot should carry the V2 compensation default
        assert body["effective_config"]["compliance_compensation_inr"] == 1000000

    async def test_invalid_config_key_rejected(self, client: AsyncClient, db_session):
        headers = await _admin_headers(client, db_session)
        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"not_a_real_key": 5}, "apply_to_existing": False},
            headers=headers,
        )
        assert resp.status_code == 422
