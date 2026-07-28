# ─────────────────────────────────────────────────────────────
#  tests/test_rbac.py  —  Module 4 (RBAC) + Module 5 (role dashboards)
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

_TOKENS: dict[str, str] = {}


async def _user_with_role(db_session, role_name: str, email: str, vendor_id=None):
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    existing = (await db_session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    role = UserRole(role_name)
    if existing:
        existing.role = role
        existing.is_admin = role == UserRole.ADMIN
        if vendor_id:
            existing.vendor_id = vendor_id
        db_session.add(existing)
    else:
        db_session.add(User(
            email=email, full_name=f"{role_name} User",
            hashed_password=hash_password("RolePass123"),
            is_admin=(role == UserRole.ADMIN), role=role, vendor_id=vendor_id,
        ))
    await db_session.commit()
    return email


async def _headers(client: AsyncClient, db_session, role_name: str, vendor_id=None):
    """Log in as a user with the given role, caching tokens to avoid the
    login rate limit."""
    email = f"{role_name.lower()}-rbac@example.com"
    key = role_name + (vendor_id or "")
    if key not in _TOKENS:
        await _user_with_role(db_session, role_name, email, vendor_id)
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "RolePass123"})
        assert resp.status_code == 200, resp.text
        _TOKENS[key] = resp.json()["access_token"]
    return {"Authorization": "Bearer " + _TOKENS[key]}


class TestPermissionMatrix:
    """The role → permission table is the contract; verify it directly."""

    def test_admin_has_config_edit(self):
        from app.utils.permissions import ROLE_PERMISSIONS, Permission
        from app.models.user import UserRole
        assert Permission.CONFIG_EDIT in ROLE_PERMISSIONS[UserRole.ADMIN]

    def test_analyst_can_view_but_not_edit_config(self):
        from app.utils.permissions import ROLE_PERMISSIONS, Permission
        from app.models.user import UserRole
        perms = ROLE_PERMISSIONS[UserRole.ANALYST]
        assert Permission.CONFIG_VIEW in perms
        assert Permission.CONFIG_EDIT not in perms

    def test_auditor_is_read_only(self):
        from app.utils.permissions import ROLE_PERMISSIONS, Permission
        from app.models.user import UserRole
        perms = ROLE_PERMISSIONS[UserRole.AUDITOR]
        assert Permission.AUDIT_VIEW in perms
        for writable in (Permission.CONFIG_EDIT, Permission.VENDOR_EDIT,
                         Permission.VENDOR_DELETE, Permission.APPROVAL_DECIDE):
            assert writable not in perms

    def test_vendor_cannot_see_all_vendors(self):
        from app.utils.permissions import ROLE_PERMISSIONS, Permission
        from app.models.user import UserRole
        perms = ROLE_PERMISSIONS[UserRole.VENDOR]
        assert Permission.VENDOR_VIEW_OWN in perms
        assert Permission.VENDOR_VIEW_ALL not in perms

    def test_only_admin_decides_approvals(self):
        from app.utils.permissions import ROLE_PERMISSIONS, Permission
        from app.models.user import UserRole
        for role in (UserRole.ANALYST, UserRole.VENDOR, UserRole.AUDITOR):
            assert Permission.APPROVAL_DECIDE not in ROLE_PERMISSIONS[role]


class TestConfigAccessByRole:
    async def test_admin_can_read_and_write_config(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        assert (await client.get("/api/v1/config/versions", headers=h)).status_code == 200
        resp = await client.put(
            "/api/v1/config/versions/2",
            json={"settings": {"expiry_warning_days": 31}, "apply_to_existing": False},
            headers=h,
        )
        assert resp.status_code == 200

    async def test_analyst_reads_config_but_cannot_edit(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ANALYST")
        assert (await client.get("/api/v1/config/versions", headers=h)).status_code == 200
        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"expiry_warning_days": 45}, "apply_to_existing": False},
            headers=h,
        )
        assert resp.status_code == 403

    async def test_auditor_reads_config_but_cannot_edit(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "AUDITOR")
        assert (await client.get("/api/v1/config/versions", headers=h)).status_code == 200
        resp = await client.put(
            "/api/v1/config/versions/1",
            json={"settings": {"expiry_warning_days": 45}, "apply_to_existing": False},
            headers=h,
        )
        assert resp.status_code == 403

    async def test_vendor_denied_config_entirely(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "VENDOR")
        assert (await client.get("/api/v1/config/versions", headers=h)).status_code == 403


class TestRoleDashboards:
    """Module 5 — each role receives a differently-shaped homepage payload."""

    async def test_admin_dashboard_includes_config(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ADMIN")
        body = (await client.get("/api/v1/dashboard/me", headers=h)).json()
        assert body["view"] == "admin"
        assert "config" in body and "summary" in body

    async def test_analyst_dashboard_has_report_no_config(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ANALYST")
        body = (await client.get("/api/v1/dashboard/me", headers=h)).json()
        assert body["view"] == "analyst"
        assert "report" in body
        assert "config" not in body

    async def test_auditor_dashboard_is_marked_read_only(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "AUDITOR")
        body = (await client.get("/api/v1/dashboard/me", headers=h)).json()
        assert body["view"] == "auditor"
        assert body.get("read_only") is True
        assert "config" not in body

    async def test_vendor_dashboard_scoped_to_own_record_only(
        self, client: AsyncClient, db_session, auth_headers
    ):
        # create a vendor and link a VENDOR user to it
        v = (await client.post("/api/v1/vendors", json={"name": "RBAC Scoped Vendor"},
                               headers=auth_headers)).json()
        h = await _headers(client, db_session, "VENDOR", vendor_id=v["id"])
        body = (await client.get("/api/v1/dashboard/me", headers=h)).json()
        assert body["view"] == "vendor"
        # sees only their own record, and no org-wide summary
        assert body["vendor"]["id"] == v["id"]
        assert "summary" not in body
        assert "my_settings" in body

    async def test_dashboard_returns_permission_list(self, client: AsyncClient, db_session):
        h = await _headers(client, db_session, "ANALYST")
        body = (await client.get("/api/v1/dashboard/me", headers=h)).json()
        assert isinstance(body["permissions"], list)
        assert "config:view" in body["permissions"]
        assert "config:edit" not in body["permissions"]


class TestVendorScoping:
    async def test_vendor_cannot_read_another_vendors_settings(
        self, client: AsyncClient, db_session, auth_headers
    ):
        own = (await client.post("/api/v1/vendors", json={"name": "Own Vendor"}, headers=auth_headers)).json()
        other = (await client.post("/api/v1/vendors", json={"name": "Other Vendor"}, headers=auth_headers)).json()
        h = await _headers(client, db_session, "VENDOR", vendor_id=own["id"])
        # own settings: allowed
        assert (await client.get(f"/api/v1/config/vendors/{own['id']}/effective", headers=h)).status_code == 200
        # someone else's: forbidden
        assert (await client.get(f"/api/v1/config/vendors/{other['id']}/effective", headers=h)).status_code == 403
