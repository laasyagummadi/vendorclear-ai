# ─────────────────────────────────────────────────────────────
#  tests/test_documents.py  —  Document upload & analysis tests
# ─────────────────────────────────────────────────────────────
import io
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio

VENDOR_PAYLOAD = {
    "name": "DocTest Vendor LLC",
    "contact_name": "Jane Smith",
    "email": "jane@doctest.com",
    "phone": "555-9999",
    "city": "Dallas",
    "state": "TX",
    "zip_code": "75201",
    "diversity_types": ["WBE"],
    "gl_expiry": "2027-06-30",
    "wc_expiry": "2027-06-30",
}

FAKE_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing"


async def _create_vendor(client: AsyncClient, auth_headers: dict) -> str:
    resp = await client.post("/api/v1/vendors", json=VENDOR_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestDocumentUpload:
    async def test_upload_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/vendors/some-id/documents",
            files={"file": ("test.pdf", io.BytesIO(FAKE_PDF_BYTES), "application/pdf")},
        )
        assert resp.status_code in (401, 403)

    @patch("app.services.file_storage_service.save_upload")
    @patch("app.services.ocr_service.extract_text", return_value="certificate of liability insurance")
    @patch("app.services.gemini_service.extract_coi", new_callable=AsyncMock)
    async def test_upload_coi_success(
        self,
        mock_gemini,
        mock_ocr,
        mock_save,
        client: AsyncClient,
        auth_headers: dict,
    ):
        mock_save.return_value = ("/tmp/fake_coi.pdf", 1234)
        mock_gemini.return_value = {
            "insured_name": "DocTest Vendor LLC",
            "insurer_name": "Acme Insurance Co",
            "policy_number": "POL-12345",
            "coverage_type": "Commercial General Liability",
            "general_liability_limit_usd": 2000000.0,
            "workers_comp_limit_usd": 500000.0,
            "auto_liability_limit_usd": None,
            "effective_date": "2025-01-01",
            "expiry_date": "2027-01-01",
            "additional_insured": True,
            "certificate_holder": "City of Dallas",
            "confidence_score": 0.92,
        }

        vendor_id = await _create_vendor(client, auth_headers)

        resp = await client.post(
            f"/api/v1/vendors/{vendor_id}/documents",
            files={"file": ("coi.pdf", io.BytesIO(FAKE_PDF_BYTES), "application/pdf")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "document" in body
        assert body["document"]["document_type"] == "COI"
        assert body["document"]["status"] == "PROCESSED"
        assert "message" in body

    async def test_upload_invalid_vendor(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/vendors/nonexistent-vendor-id/documents",
            files={"file": ("test.pdf", io.BytesIO(FAKE_PDF_BYTES), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_list_documents_empty(self, client: AsyncClient, auth_headers: dict):
        vendor_id = await _create_vendor(client, auth_headers)
        resp = await client.get(f"/api/v1/vendors/{vendor_id}/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_document_not_found(self, client: AsyncClient, auth_headers: dict):
        vendor_id = await _create_vendor(client, auth_headers)
        resp = await client.get(
            f"/api/v1/vendors/{vendor_id}/documents/nonexistent-doc-id",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestAnalysisEndpoint:
    async def test_get_analysis_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/analyses/nonexistent-analysis-id",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_analysis_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/analyses/some-id")
        assert resp.status_code in (401, 403)
