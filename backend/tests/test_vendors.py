# ─────────────────────────────────────────────────────────────
#  tests/test_vendors.py  —  Vendor CRUD endpoint tests
# ─────────────────────────────────────────────────────────────
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

VENDOR_PAYLOAD = {
    "name": "Acme Construction LLC",
    "contact_name": "John Doe",
    "email": "john@acme.com",
    "phone": "555-1234",
    "city": "Houston",
    "state": "TX",
    "zip_code": "77001",
    "diversity_types": ["MBE"],
    "gl_expiry": "2027-12-31",
    "wc_expiry": "2027-12-31",
}


class TestCreateVendor:
    async def test_create_success(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Acme Construction LLC"
        assert body["status"] == "NEEDS_REVIEW"
        assert body["risk_tier"] == "MEDIUM"
        assert "id" in body

    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/vendors", json=VENDOR_PAYLOAD)
        assert resp.status_code in (401, 403)

    async def test_create_empty_name(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/vendors",
            json={**VENDOR_PAYLOAD, "name": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_invalid_date_format(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/vendors",
            json={**VENDOR_PAYLOAD, "gl_expiry": "31-12-2027"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestListVendors:
    async def test_list_success(self, client: AsyncClient, auth_headers):
        # Create a vendor first
        await client.post("/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers)

        resp = await client.get("/api/v1/vendors", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "total" in body
        assert body["page"] == 1
        assert isinstance(body["data"], list)

    async def test_list_pagination(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors?page=1&page_size=5", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page_size"] == 5

    async def test_list_filter_by_status(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors?status=NEEDS_REVIEW", headers=auth_headers
        )
        assert resp.status_code == 200
        for v in resp.json()["data"]:
            assert v["status"] == "NEEDS_REVIEW"

    async def test_list_search(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors?search=Acme", headers=auth_headers
        )
        assert resp.status_code == 200


class TestGetVendor:
    async def test_get_success(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        vendor_id = create.json()["id"]

        resp = await client.get(f"/api/v1/vendors/{vendor_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == vendor_id

    async def test_get_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors/nonexistent-id", headers=auth_headers
        )
        assert resp.status_code == 404


class TestUpdateVendor:
    async def test_update_success(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        vendor_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/vendors/{vendor_id}",
            json={"name": "Acme Updated LLC", "city": "Austin"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Acme Updated LLC"
        assert body["city"] == "Austin"

    async def test_update_compliance_fields(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        vendor_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/vendors/{vendor_id}",
            json={"status": "COMPLIANT", "risk_tier": "LOW", "compliance_score": 92.5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "COMPLIANT"
        assert body["compliance_score"] == 92.5


class TestDeleteVendor:
    async def test_soft_delete(self, client: AsyncClient, auth_headers):
        create = await client.post(
            "/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers
        )
        vendor_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/vendors/{vendor_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Should no longer appear in default list (is_active=True filter)
        list_resp = await client.get("/api/v1/vendors", headers=auth_headers)
        ids = [v["id"] for v in list_resp.json()["data"]]
        assert vendor_id not in ids

    async def test_delete_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.delete(
            "/api/v1/vendors/nonexistent-id", headers=auth_headers
        )
        assert resp.status_code == 404


class TestVendorAlerts:
    async def test_expiring_soon(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors/alerts/expiring-soon?days=365", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_status_summary(self, client: AsyncClient, auth_headers):
        resp = await client.get(
            "/api/v1/vendors/stats/summary", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "compliant" in body
        assert "needs_review" in body
        assert "non_compliant" in body
