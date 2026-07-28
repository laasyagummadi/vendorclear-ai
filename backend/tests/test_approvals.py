# ─────────────────────────────────────────────────────────────
#  tests/test_approvals.py  —  Module 9 approval workflow
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

_TOK: dict[str, str] = {}


async def _headers(client: AsyncClient, db_session, role_name: str, vendor_id=None):
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    email = f"{role_name.lower()}-appr@example.com"
    key = role_name + (vendor_id or "")
    if key not in _TOK:
        role = UserRole(role_name)
        existing = (await db_session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            existing.role = role
            existing.is_admin = role == UserRole.ADMIN
            if vendor_id:
                existing.vendor_id = vendor_id
            db_session.add(existing)
        else:
            db_session.add(User(
                email=email, full_name=f"{role_name} Appr",
                hashed_password=hash_password("ApprPass123"),
                is_admin=(role == UserRole.ADMIN), role=role, vendor_id=vendor_id,
            ))
        await db_session.commit()
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "ApprPass123"})
        assert resp.status_code == 200, resp.text
        _TOK[key] = resp.json()["access_token"]
    return {"Authorization": "Bearer " + _TOK[key]}


CONSTRUCTION = {
    "name": "Construction Policy",
    "category": "Construction",
    "version": 1,
    "description": "High-risk construction requirements",
    "requirements": {
        "required_gl_limit_usd": 5000000,
        "workers_comp_required": True,
        "umbrella_required": True,
    },
}


class TestPolicyManagement:
    async def test_admin_creates_policy(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        resp = await client.post("/api/v1/policies", json=CONSTRUCTION, headers=h)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Construction Policy"
        assert body["requirements"]["required_gl_limit_usd"] == 5000000

    async def test_analyst_cannot_create_policy(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ANALYST")
        resp = await client.post("/api/v1/policies", json=CONSTRUCTION, headers=h)
        assert resp.status_code == 403

    async def test_analyst_can_list_policies(self, client: AsyncClient, db_session):
        admin = await _headers(client, db_session, "ADMIN")
        await client.post("/api/v1/policies", json=CONSTRUCTION, headers=admin)
        h = await _headers(client, db_session, "ANALYST")
        resp = await client.get("/api/v1/policies", headers=h)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_vendor_cannot_list_policies(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "VENDOR")
        assert (await client.get("/api/v1/policies", headers=h)).status_code == 403


class TestSubmissionFlow:
    async def _policy_and_vendor(self, client, admin_h):
        pol = (await client.post("/api/v1/policies", json=CONSTRUCTION, headers=admin_h)).json()
        vend = (await client.post("/api/v1/vendors", json={"name": "Approval Test Vendor"},
                                  headers=admin_h)).json()
        return pol["id"], vend["id"]

    async def test_submission_starts_pending_and_checks_requirements(
        self, client: AsyncClient, db_session
    ):
        h = await _headers(client, db_session, "ADMIN")
        pid, vid = await self._policy_and_vendor(client, h)
        resp = await client.post(
            "/api/v1/policies/submissions",
            json={"policy_id": pid, "vendor_id": vid}, headers=h,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "PENDING"
        # requirements were evaluated automatically
        results = body["requirement_results"]
        assert "general_liability" in results
        assert "workers_comp" in results
        assert "umbrella" in results
        # vendor has no documents, so it should not meet requirements
        assert body["meets_requirements"] is False

    async def test_admin_approval_makes_submission_active(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        pid, vid = await self._policy_and_vendor(client, h)
        sub = (await client.post("/api/v1/policies/submissions",
                                 json={"policy_id": pid, "vendor_id": vid}, headers=h)).json()
        resp = await client.post(
            f"/api/v1/policies/submissions/{sub['id']}/approve",
            json={"notes": "Manually verified."}, headers=h,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # per spec: approval activates the submission
        assert body["status"] == "ACTIVE"
        assert body["review_notes"] == "Manually verified."
        assert body["reviewed_at"] is not None

    async def test_rejection_records_reviewer_and_notes(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        pid, vid = await self._policy_and_vendor(client, h)
        sub = (await client.post("/api/v1/policies/submissions",
                                 json={"policy_id": pid, "vendor_id": vid}, headers=h)).json()
        resp = await client.post(
            f"/api/v1/policies/submissions/{sub['id']}/reject",
            json={"notes": "GL limit insufficient."}, headers=h,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"
        assert resp.json()["review_notes"] == "GL limit insufficient."


class TestDecisionAuthority:
    """Only ADMIN holds APPROVAL_DECIDE."""

    async def _pending_submission(self, client, admin_h):
        pol = (await client.post("/api/v1/policies", json=CONSTRUCTION, headers=admin_h)).json()
        vend = (await client.post("/api/v1/vendors", json={"name": "Authority Vendor"},
                                  headers=admin_h)).json()
        return (await client.post("/api/v1/policies/submissions",
                                  json={"policy_id": pol["id"], "vendor_id": vend["id"]},
                                  headers=admin_h)).json()["id"]

    @pytest.mark.parametrize("role", ["ANALYST", "AUDITOR", "VENDOR"])
    async def test_non_admin_cannot_approve(self, client: AsyncClient, db_session, role):
        admin_h = await _headers(client, db_session, "ADMIN")
        sid = await self._pending_submission(client, admin_h)
        h = await _headers(client, db_session, role)
        resp = await client.post(f"/api/v1/policies/submissions/{sid}/approve",
                                 json={"notes": "x"}, headers=h)
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["ANALYST", "AUDITOR", "VENDOR"])
    async def test_non_admin_cannot_reject(self, client: AsyncClient, db_session, role):
        admin_h = await _headers(client, db_session, "ADMIN")
        sid = await self._pending_submission(client, admin_h)
        h = await _headers(client, db_session, role)
        resp = await client.post(f"/api/v1/policies/submissions/{sid}/reject",
                                 json={"notes": "x"}, headers=h)
        assert resp.status_code == 403


class TestStateMachine:
    async def test_cannot_approve_an_already_active_submission(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        pol = (await client.post("/api/v1/policies", json=CONSTRUCTION, headers=h)).json()
        vend = (await client.post("/api/v1/vendors", json={"name": "SM Vendor"}, headers=h)).json()
        sub = (await client.post("/api/v1/policies/submissions",
                                 json={"policy_id": pol["id"], "vendor_id": vend["id"]},
                                 headers=h)).json()
        first = await client.post(f"/api/v1/policies/submissions/{sub['id']}/approve",
                                  json={}, headers=h)
        assert first.status_code == 200
        assert first.json()["status"] == "ACTIVE"
        # approving again is an invalid transition
        second = await client.post(f"/api/v1/policies/submissions/{sub['id']}/approve",
                                   json={}, headers=h)
        assert second.status_code == 409

    async def test_transition_matrix_blocks_illegal_jumps(self):
        from app.services.approval_service import ALLOWED_TRANSITIONS
        from app.models.policy import SubmissionStatus
        # a rejected submission may only go back to pending
        assert ALLOWED_TRANSITIONS[SubmissionStatus.REJECTED] == {SubmissionStatus.PENDING}
        # you cannot go straight from draft to active
        assert SubmissionStatus.ACTIVE not in ALLOWED_TRANSITIONS[SubmissionStatus.DRAFT]


class TestVendorScoping:
    async def test_vendor_only_sees_own_submissions(self, client: AsyncClient, db_session):
        admin_h = await _headers(client, db_session, "ADMIN")
        pol = (await client.post("/api/v1/policies", json=CONSTRUCTION, headers=admin_h)).json()
        mine = (await client.post("/api/v1/vendors", json={"name": "Mine"}, headers=admin_h)).json()
        theirs = (await client.post("/api/v1/vendors", json={"name": "Theirs"}, headers=admin_h)).json()
        for vid in (mine["id"], theirs["id"]):
            await client.post("/api/v1/policies/submissions",
                              json={"policy_id": pol["id"], "vendor_id": vid}, headers=admin_h)

        h = await _headers(client, db_session, "VENDOR", vendor_id=mine["id"])
        rows = (await client.get("/api/v1/policies/submissions", headers=h)).json()
        assert all(r["vendor_id"] == mine["id"] for r in rows)
