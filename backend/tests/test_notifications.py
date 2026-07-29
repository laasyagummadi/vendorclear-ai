# ─────────────────────────────────────────────────────────────
#  tests/test_notifications.py  —  Vendor alert email tests
# ─────────────────────────────────────────────────────────────
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from config import settings
from app.services import email_service as email_service_module
from app.services.notification_service import NotificationService
from app.models.notification_log import NotificationTrigger

pytestmark = pytest.mark.asyncio


def _expiring_vendor_payload(days_from_now: int, email: str = "vendor@example.com"):
    expiry = (date.today() + timedelta(days=days_from_now)).isoformat()
    return {
        "name": "Notify Test Vendor",
        "email": email,
        "gl_expiry": expiry,
    }


class TestNotifyEndpointDisabled:
    async def test_notify_reports_disabled_when_smtp_not_configured(self, client: AsyncClient, auth_headers):
        # Default test settings have alerts_email_enabled=False / no SMTP —
        # the endpoint should no-op cleanly rather than error.
        resp = await client.post("/api/v1/alerts/notify", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 0
        assert "disabled_reason" in body

    async def test_notify_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/alerts/notify")
        assert resp.status_code in (401, 403)


class TestNotificationServiceSending(object):
    """Exercises the service directly with SMTP enabled but the actual
    send call monkeypatched, so no real network activity occurs."""

    async def test_sends_and_dedupes_by_urgency_bucket(self, db_session, client: AsyncClient, auth_headers, monkeypatch):
        # Create a vendor via the API so it goes through normal creation,
        # then give it a GL policy expiring in 5 days (falls in the "7"
        # urgency bucket).
        payload = _expiring_vendor_payload(days_from_now=5)
        resp = await client.post("/api/v1/vendors", json=payload, headers=auth_headers)
        assert resp.status_code == 201

        # Enable alerts + fake SMTP config so EmailService.is_enabled() is True.
        monkeypatch.setattr(settings, "alerts_email_enabled", True)
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings, "smtp_user", "alerts@example.com")
        monkeypatch.setattr(settings, "smtp_password", "fake-password")

        sent_emails = []

        async def fake_send_email(to_email, subject, html_body, text_body):
            sent_emails.append(to_email)

        monkeypatch.setattr(email_service_module.email_service, "send_email", fake_send_email)

        svc = NotificationService(db_session)
        result = await svc.run(trigger=NotificationTrigger.MANUAL, expiry_days=30)

        assert result["sent"] == 1
        assert sent_emails == ["vendor@example.com"]

        # Running again immediately should NOT re-send — same vendor, same
        # urgency bucket, already logged.
        sent_emails.clear()
        result2 = await svc.run(trigger=NotificationTrigger.MANUAL, expiry_days=30)
        assert result2["sent"] == 0
        assert sent_emails == []

    async def test_skips_vendor_with_no_email_on_file(self, db_session, client: AsyncClient, auth_headers, monkeypatch):
        payload = {
            "name": "No Email Vendor",
            "gl_expiry": (date.today() + timedelta(days=3)).isoformat(),
        }
        resp = await client.post("/api/v1/vendors", json=payload, headers=auth_headers)
        assert resp.status_code == 201

        monkeypatch.setattr(settings, "alerts_email_enabled", True)
        monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
        monkeypatch.setattr(settings, "smtp_user", "alerts@example.com")
        monkeypatch.setattr(settings, "smtp_password", "fake-password")

        async def fake_send_email(*args, **kwargs):
            raise AssertionError("should not attempt to send when vendor has no email")

        monkeypatch.setattr(email_service_module.email_service, "send_email", fake_send_email)

        svc = NotificationService(db_session)
        result = await svc.run(trigger=NotificationTrigger.SCHEDULED, expiry_days=30)
        assert result["skipped_no_email"] >= 1
