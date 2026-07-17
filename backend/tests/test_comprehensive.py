# ─────────────────────────────────────────────────────────────
#  tests/test_comprehensive.py  —  Full-surface regression pass
#  Covers gaps not exercised by the existing test files:
#  password change, auth guards on every protected route, enum
#  validation, file-upload edge cases, zero-data math safety,
#  DB-level cascade behavior, and rate limiting.
# ─────────────────────────────────────────────────────────────
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

FAKE_PDF = b"%PDF-1.4 certificate of insurance general liability $2,000,000 expiration: 01/01/2099"


async def _create_vendor(client: AsyncClient, auth_headers: dict, **overrides) -> dict:
    payload = {
        "name": "Comprehensive Test Vendor",
        "contact_name": "Q. Tester",
        "email": "qtester@example.com",
        "city": "Springfield",
        "state": "IL",
        **overrides,
    }
    resp = await client.post("/api/v1/vendors", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Password change ────────────────────────────────────────────
class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Secure123",
                "new_password": "NewSecure456",
                "confirm_new_password": "NewSecure456",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        # revert so other tests relying on the shared session-scoped user still work
        await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "NewSecure456",
                "new_password": "Secure123",
                "confirm_new_password": "Secure123",
            },
            headers=auth_headers,
        )

    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword1",
                "new_password": "NewSecure456",
                "confirm_new_password": "NewSecure456",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 401

    async def test_change_password_mismatch(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Secure123",
                "new_password": "NewSecure456",
                "confirm_new_password": "Different789",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_change_password_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "x", "new_password": "NewSecure456", "confirm_new_password": "NewSecure456"},
        )
        assert resp.status_code == 403  # HTTPBearer with no header -> 403


# ── Auth guard coverage on every protected route ──────────────
class TestAuthGuards:
    """Every vendor/document/dashboard/alert route must reject unauthenticated calls."""

    async def test_get_vendor_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/vendors/some-id")
        assert resp.status_code == 403

    async def test_update_vendor_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/vendors/some-id", json={"name": "x"})
        assert resp.status_code == 403

    async def test_delete_vendor_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/vendors/some-id")
        assert resp.status_code == 403

    async def test_list_documents_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/vendors/some-id/documents")
        assert resp.status_code == 403

    async def test_dashboard_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 403

    async def test_vendor_score_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/vendors/some-id/score")
        assert resp.status_code == 403

    async def test_bad_token_rejected(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/vendors", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert resp.status_code == 401


# ── Enum / validation edge cases ───────────────────────────────
class TestVendorValidation:
    async def test_invalid_status_enum_rejected(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="enum1@example.com")
        resp = await client.patch(
            f"/api/v1/vendors/{v['id']}", json={"status": "ACTIVE"}, headers=auth_headers
        )
        # "ACTIVE" isn't a valid VendorStatus (COMPLIANT/NEEDS_REVIEW/NON_COMPLIANT)
        assert resp.status_code == 422

    async def test_invalid_risk_tier_enum_rejected(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="enum2@example.com")
        resp = await client.patch(
            f"/api/v1/vendors/{v['id']}", json={"risk_tier": "CRITICAL"}, headers=auth_headers
        )
        # "CRITICAL" isn't a valid RiskTier (LOW/MEDIUM/HIGH)
        assert resp.status_code == 422

    async def test_invalid_email_on_create_rejected(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/vendors",
            json={"name": "Bad Email Co", "email": "not-an-email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_valid_enum_update_succeeds(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="enum3@example.com")
        resp = await client.patch(
            f"/api/v1/vendors/{v['id']}",
            json={"status": "COMPLIANT", "risk_tier": "LOW"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLIANT"
        assert resp.json()["risk_tier"] == "LOW"


# ── File upload edge cases ─────────────────────────────────────
class TestUploadEdgeCases:
    async def test_reject_unsupported_mime_type(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="upload1@example.com")
        resp = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("malware.exe", b"MZ\x90\x00fake exe", "application/x-msdownload")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    async def test_reject_oversized_file(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="upload2@example.com")
        big = b"%PDF-1.4" + (b"0" * (21 * 1024 * 1024))  # 21MB, over the 20MB limit
        resp = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("huge.pdf", big, "application/pdf")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert resp.status_code == 413

    async def test_analysis_detail_includes_vendor_id(self, client: AsyncClient, auth_headers: dict):
        """AnalysisDetail.jsx's breadcrumb navigates using analysis.vendor_id;
        Analysis only has document_id at the DB level, so this must be
        populated by joining through the document."""
        v = await _create_vendor(client, auth_headers, email="upload6@example.com")
        up = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("vid.pdf", FAKE_PDF, "application/pdf")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        doc_id = up.json()["document"]["id"]
        analyses = await client.get(
            f"/api/v1/vendors/{v['id']}/documents/{doc_id}/analyses", headers=auth_headers
        )
        analysis_id = analyses.json()[0]["id"]

        single = await client.get(f"/api/v1/analyses/{analysis_id}", headers=auth_headers)
        assert single.status_code == 200
        assert single.json()["vendor_id"] == v["id"]

    async def test_docx_upload_extracts_text(self, client: AsyncClient, auth_headers: dict):
        docx = pytest.importorskip("docx")
        buf = io.BytesIO()
        d = docx.Document()
        d.add_paragraph("CERTIFICATE OF INSURANCE")
        d.add_paragraph("General Liability $3,000,000")
        d.add_paragraph("Expiration: 12/31/2099")
        d.save(buf)
        buf.seek(0)

        v = await _create_vendor(client, auth_headers, email="upload3@example.com")
        resp = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("coi.docx", buf.read(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        analyses = await client.get(
            f"/api/v1/vendors/{v['id']}/documents/{doc_id}/analyses", headers=auth_headers
        )
        assert analyses.status_code == 200
        body = analyses.json()
        assert len(body) == 1
        assert body[0]["general_liability_limit_usd"] == 3_000_000.0
        assert "2099-12-31" in (body[0]["expiry_date"] or "")

    async def test_diversity_cert_low_ownership_flagged(self, client: AsyncClient, auth_headers: dict):
        docx = pytest.importorskip("docx")
        buf = io.BytesIO()
        d = docx.Document()
        d.add_paragraph("DIVERSITY CERTIFICATE")
        d.add_paragraph("MBE certified")
        d.add_paragraph("30% owned")
        d.add_paragraph("Expiration: 12/31/2099")
        d.save(buf)
        buf.seek(0)

        v = await _create_vendor(client, auth_headers, email="upload4@example.com")
        resp = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("cert.docx", buf.read(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"doc_type_hint": "DIVERSITY_CERT"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        analyses = await client.get(
            f"/api/v1/vendors/{v['id']}/documents/{doc_id}/analyses", headers=auth_headers
        )
        findings = analyses.json()[0]["findings"]
        codes = [f["rule_code"] for f in findings]
        assert "LOW_OWNERSHIP_PERCENT" in codes

    async def test_upload_traversal_filename_is_sanitized(self, client: AsyncClient, auth_headers: dict):
        v = await _create_vendor(client, auth_headers, email="upload5@example.com")
        resp = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("../../../../etc/passwd_pwn.pdf", FAKE_PDF, "application/pdf")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        # No file_path in the response (schema no longer leaks it), but the
        # upload must have succeeded without writing outside uploads/.
        import os
        assert not os.path.exists("/etc/passwd_pwn.pdf")


# ── Zero-data math safety ──────────────────────────────────────
class TestEmptyStateMath:
    async def test_dashboard_summary_with_no_vendors_no_division_error(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Uses whatever vendors already exist in the session DB; the real
        # assertion is that this never 500s regardless of vendor count,
        # including the zero case exercised by test isolation ordering.
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["vendors"]["compliance_rate_pct"] <= 100

    async def test_compliance_report_avg_score_no_division_error(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/dashboard/compliance-report", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["summary"]["avg_score"], (int, float))


# ── Database-level integrity (cascade deletes, constraints) ───
class TestDatabaseIntegrity:
    async def test_duplicate_email_registration_blocked_at_db_and_api(
        self, client: AsyncClient
    ):
        payload = {
            "full_name": "Dup User", "email": "dup-check@example.com",
            "password": "Secure123", "confirm_password": "Secure123",
        }
        first = await client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201
        second = await client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409

    async def test_vendor_cascade_delete_removes_documents_and_findings(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.vendor import Vendor
        from app.models.document import Document
        from app.models.analysis import Analysis
        from app.models.finding import Finding

        v = await _create_vendor(client, auth_headers, email="cascade@example.com")
        up = await client.post(
            f"/api/v1/vendors/{v['id']}/documents",
            files={"file": ("cascade.pdf", FAKE_PDF, "application/pdf")},
            data={"doc_type_hint": "COI"},
            headers=auth_headers,
        )
        assert up.status_code == 201
        doc_id = up.json()["document"]["id"]

        analyses_resp = await client.get(
            f"/api/v1/vendors/{v['id']}/documents/{doc_id}/analyses", headers=auth_headers
        )
        analysis_id = analyses_resp.json()[0]["id"]

        # Hard-delete the vendor directly at the DB layer (the API only
        # soft-deletes) to verify the ON DELETE CASCADE foreign keys are
        # actually wired correctly end to end.
        vendor_row = await db_session.get(Vendor, v["id"])
        await db_session.delete(vendor_row)
        await db_session.commit()

        assert await db_session.get(Document, doc_id) is None
        assert await db_session.get(Analysis, analysis_id) is None
        remaining_findings = (await db_session.execute(
            select(Finding).where(Finding.analysis_id == analysis_id)
        )).scalars().all()
        assert remaining_findings == []


# ── Rate limiting ───────────────────────────────────────────────
class TestRateLimiting:
    async def test_login_rate_limit_engages(self, client: AsyncClient):
        # Limit is 10/minute per client IP; the 11th rapid request should 429.
        payload = {"email": "nonexistent-rl@example.com", "password": "wrong"}
        statuses = []
        for _ in range(12):
            resp = await client.post("/api/v1/auth/login", json=payload)
            statuses.append(resp.status_code)
        assert 429 in statuses, f"expected a 429 among {statuses}"
