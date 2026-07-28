# ─────────────────────────────────────────────────────────────
#  tests/test_audit.py  —  M7 audit trail + M8 version history
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

_TOK: dict[str, str] = {}


async def _headers(client: AsyncClient, db_session, role_name: str):
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    email = f"{role_name.lower()}-audit@example.com"
    if role_name not in _TOK:
        role = UserRole(role_name)
        existing = (await db_session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            existing.role = role
            existing.is_admin = role == UserRole.ADMIN
            db_session.add(existing)
        else:
            db_session.add(User(
                email=email, full_name=f"{role_name} Audit",
                hashed_password=hash_password("AuditPass123"),
                is_admin=(role == UserRole.ADMIN), role=role,
            ))
        await db_session.commit()
        resp = await client.post("/api/v1/auth/login",
                                 json={"email": email, "password": "AuditPass123"})
        assert resp.status_code == 200, resp.text
        _TOK[role_name] = resp.json()["access_token"]
    return {"Authorization": "Bearer " + _TOK[role_name]}


class TestAuditTrail:
    async def test_config_change_is_logged(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        await client.put("/api/v1/config/versions/1",
                         json={"settings": {"expiry_warning_days": 33},
                               "apply_to_existing": False}, headers=h)
        logs = (await client.get("/api/v1/audit/logs?entity_type=version_config", headers=h)).json()
        assert logs["total"] >= 1
        entry = logs["logs"][0]
        assert entry["action"] == "CONFIG_CHANGE"
        assert entry["actor_email"] == "admin-audit@example.com"
        assert entry["actor_role"] == "ADMIN"
        # the diff records what actually changed
        assert "expiry_warning_days" in (entry["changes"] or {})

    async def test_approval_decision_is_logged(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        pol = (await client.post("/api/v1/policies", json={
            "name": "Audit Policy", "version": 1,
            "requirements": {"required_gl_limit_usd": 1000000},
        }, headers=h)).json()
        vend = (await client.post("/api/v1/vendors", json={"name": "Audit Vendor"}, headers=h)).json()
        sub = (await client.post("/api/v1/policies/submissions",
                                 json={"policy_id": pol["id"], "vendor_id": vend["id"]},
                                 headers=h)).json()
        await client.post(f"/api/v1/policies/submissions/{sub['id']}/approve",
                          json={"notes": "Looks good"}, headers=h)
        logs = (await client.get("/api/v1/audit/logs?entity_type=policy_submission",
                                 headers=h)).json()
        actions = [l["action"] for l in logs["logs"]]
        assert "APPROVE" in actions

    async def test_audit_log_never_stores_sensitive_fields(self, client: AsyncClient, db_session):
        from app.services.audit_service import _scrub
        cleaned = _scrub({"email": "x@y.com", "hashed_password": "secret", "gemini_api_key": "k"})
        assert "hashed_password" not in cleaned
        assert "gemini_api_key" not in cleaned
        assert cleaned["email"] == "x@y.com"

    async def test_auditor_can_read_logs(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "AUDITOR")
        assert (await client.get("/api/v1/audit/logs", headers=h)).status_code == 200

    async def test_analyst_cannot_read_logs(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ANALYST")
        assert (await client.get("/api/v1/audit/logs", headers=h)).status_code == 403

    async def test_vendor_cannot_read_logs(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "VENDOR")
        assert (await client.get("/api/v1/audit/logs", headers=h)).status_code == 403


class TestVersionHistory:
    async def test_config_edits_accumulate_versions(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        # two successive edits
        await client.put("/api/v1/config/versions/2",
                         json={"settings": {"expiry_warning_days": 21}, "apply_to_existing": False},
                         headers=h)
        await client.put("/api/v1/config/versions/2",
                         json={"settings": {"expiry_warning_days": 22}, "apply_to_existing": False},
                         headers=h)

        from app.models.version_config import VersionConfig
        row = (await db_session.execute(
            select(VersionConfig).where(VersionConfig.version == 2))).scalar_one()
        hist = (await client.get(f"/api/v1/audit/history/version_config/{row.id}", headers=h)).json()
        assert len(hist["versions"]) >= 2
        newest = hist["versions"][0]
        # M8 requirement: store version, date, uploader, changes
        assert newest["version"] >= 2
        assert newest["date"] is not None
        assert newest["uploader"] == "admin-audit@example.com"
        assert "expiry_warning_days" in (newest["changes"] or {})

    async def test_can_fetch_a_specific_version(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        await client.put("/api/v1/config/versions/1",
                         json={"settings": {"expiry_critical_days": 5}, "apply_to_existing": False},
                         headers=h)
        from app.models.version_config import VersionConfig
        row = (await db_session.execute(
            select(VersionConfig).where(VersionConfig.version == 1))).scalar_one()
        hist = (await client.get(f"/api/v1/audit/history/version_config/{row.id}", headers=h)).json()
        n = hist["versions"][0]["version"]
        one = (await client.get(f"/api/v1/audit/history/version_config/{row.id}/{n}",
                                headers=h)).json()
        assert one["version"] == n
        assert "snapshot" in one

    async def test_diff_helper_computes_field_changes(self):
        from app.services.audit_service import diff
        d = diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
        assert d["b"] == {"from": 2, "to": 3}
        assert d["c"] == {"from": None, "to": 4}
        assert "a" not in d
