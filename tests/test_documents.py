import asyncio
import pytest
import io
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app
from app.models.vendor import Vendor
from app.models.document import DocumentType, DocumentStatus
from app.models.analysis import AnalysisStatus
from app.api.v1.documents import router as documents_router

# Dynamically mount the documents router for our test client
routes_paths = [route.path for route in app.routes if hasattr(route, "path")]
if "/api/v1/upload" not in routes_paths:
    app.include_router(documents_router, prefix="/api/v1")

@pytest.mark.anyio
async def test_full_document_pipeline(client: AsyncClient, auth_headers: dict):
    # 1. Create a vendor in the test database
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as session:
        vendor = Vendor(name="Test Contractor Inc.")
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

    mock_text = (
        "CERTIFICATE OF LIABILITY INSURANCE\n"
        "INSURED: Test Contractor Inc.\n"
        "INSURER: SafeCare Insurance Group\n"
        "POLICY NUMBER: COI-987654321-GL\n"
        "COVERAGE: GENERAL LIABILITY\n"
        "LIMIT: 1,500,000\n"
        "EFFECTIVE DATE: 2026-01-01\n"
        "EXPIRY DATE: 2026-12-31\n"
        "ADDITIONAL INSURED: Yes\n"
        "CERTIFICATE HOLDER: Utility Co LLC\n"
    )

    # 2. Upload file and mock the OCR extraction
    with patch("app.services.ocr_service.extract_text", return_value=mock_text):
        dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy contents")
        
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("acord25_sample.pdf", dummy_pdf, "application/pdf")},
            data={"vendor_id": str(vendor_id), "doc_type_hint": "COI"},
            headers=auth_headers
        )
        
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "document_id" in data
        assert "confidence_score" in data
        assert "status" in data
        
        # Verify parsed properties
        assert data["insured_name"] == "Test Contractor Inc."
        assert data["status"] == "COMPLIANT"  # No critical/high findings
        assert data["additional_insured"] is True
        
        analysis_id = data["id"]
        document_id = data["document_id"]

        # 3. Retrieve analysis details
        resp = await client.get(f"/api/v1/analysis/{analysis_id}", headers=auth_headers)
        assert resp.status_code == 200
        analysis_data = resp.json()
        assert analysis_data["id"] == analysis_id
        assert analysis_data["document_id"] == document_id

        # 4. Retrieve findings
        resp = await client.get(f"/api/v1/analysis/{analysis_id}/findings", headers=auth_headers)
        assert resp.status_code == 200
        findings = resp.json()
        assert isinstance(findings, list)
        assert len(findings) == 0  # Should be compliant

        # 5. Retrieve vendor documents
        resp = await client.get(f"/api/v1/documents/vendor/{vendor_id}", headers=auth_headers)
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) == 1
        assert docs[0]["id"] == document_id
        assert docs[0]["status"] == "PROCESSED"
        assert docs[0]["document_type"] == "COI"

@pytest.mark.anyio
async def test_expired_document_findings(client: AsyncClient, auth_headers: dict):
    # 1. Create a vendor in the test database
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as session:
        vendor = Vendor(name="Expired Vendor Corp")
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

    mock_text = (
        "CERTIFICATE OF LIABILITY INSURANCE\n"
        "INSURED: Expired Vendor Corp\n"
        "INSURER: SafeCare Insurance Group\n"
        "POLICY NUMBER: COI-EXPIRED-GL\n"
        "COVERAGE: GENERAL LIABILITY\n"
        "LIMIT: 1,500,000\n"
        "EFFECTIVE DATE: 2025-01-01\n"
        "EXPIRY DATE: 2025-12-31\n"  # Past date (expired relative to current time 2026-07-07)
    )

    # 2. Upload file with past date (expired) and mock OCR
    with patch("app.services.ocr_service.extract_text", return_value=mock_text):
        dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy contents")
        
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("expired_coi.pdf", dummy_pdf, "application/pdf")},
            data={"vendor_id": str(vendor_id), "doc_type_hint": "COI"},
            headers=auth_headers
        )
        
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        
        # Verify status is NON_COMPLIANT due to expiration
        assert data["status"] == "NON_COMPLIANT"
        
        analysis_id = data["id"]
        
        # 3. Verify findings list has DOCUMENT_EXPIRED
        resp = await client.get(f"/api/v1/analysis/{analysis_id}/findings", headers=auth_headers)
        assert resp.status_code == 200
        findings = resp.json()
        assert len(findings) > 0
        rule_codes = [f["rule_code"] for f in findings]
        assert "DOCUMENT_EXPIRED" in rule_codes
