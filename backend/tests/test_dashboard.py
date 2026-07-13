# ─────────────────────────────────────────────────────────────
#  tests/test_dashboard.py  —  Dashboard, alerts, compliance tests
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

VENDOR_PAYLOAD = {
    "name": "Dashboard Test Vendor",
    "contact_name": "Sam Lee",
    "email": "sam@dashtest.com",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "diversity_types": ["MBE"],
    "gl_expiry": "2027-12-31",
    "wc_expiry": "2027-12-31",
}


class TestDashboardSummary:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code in (401, 403)

    async def test_summary_structure(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "vendors" in body
        assert "risk_tiers" in body
        assert "documents" in body
        assert "analyses" in body
        assert "alerts" in body
        assert "generated_at" in body

    async def test_summary_counts_update(self, client: AsyncClient, auth_headers: dict):
        # Create a vendor so counts > 0
        await client.post("/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers)
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        body = resp.json()
        assert body["vendors"]["total"] >= 1

    async def test_compliance_rate_range(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        rate = resp.json()["vendors"]["compliance_rate_pct"]
        assert 0.0 <= rate <= 100.0


class TestComplianceReport:
    async def test_report_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/compliance-report")
        assert resp.status_code in (401, 403)

    async def test_report_structure(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/dashboard/compliance-report", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "report_date" in body
        assert "summary" in body
        assert "vendors" in body
        assert isinstance(body["vendors"], list)


class TestVendorScore:
    async def test_score_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/dashboard/vendors/nonexistent-id/score", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "error" in resp.json()

    async def test_score_structure(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        vendor_id = create.json()["id"]
        resp = await client.get(
            f"/api/v1/dashboard/vendors/{vendor_id}/score", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_score" in body
        assert "breakdown" in body
        assert "grade" in body
        assert 0 <= body["total_score"] <= 100
        assert body["grade"] in ["A", "B", "C", "D", "F"]


class TestAlerts:
    async def test_all_alerts_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/alerts")
        assert resp.status_code in (401, 403)

    async def test_all_alerts_structure(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/alerts", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "expiry_alerts" in body
        assert "compliance_alerts" in body
        assert isinstance(body["expiry_alerts"], list)
        assert isinstance(body["compliance_alerts"], list)

    async def test_expiry_alerts_endpoint(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/alerts/expiry?days=30", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_compliance_alerts_endpoint(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/alerts/compliance", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_alerts_with_expiring_vendor(self, client: AsyncClient, auth_headers: dict):
        # Create vendor expiring very soon (within 30 days)
        from datetime import date, timedelta
        expiry = (date.today() + timedelta(days=10)).isoformat()
        payload = {**VENDOR_PAYLOAD, "gl_expiry": expiry, "wc_expiry": expiry, "name": "Expiring Vendor"}
        await client.post("/api/v1/vendors", json=payload, headers=auth_headers)

        resp = await client.get("/api/v1/alerts/expiry?days=30", headers=auth_headers)
        alerts = resp.json()
        names = [a["vendor_name"] for a in alerts]
        assert "Expiring Vendor" in names
