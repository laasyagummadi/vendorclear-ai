# ─────────────────────────────────────────────────────────────
#  app/services/email_service.py  —  Module 6: SMTP notifications
# ─────────────────────────────────────────────────────────────
"""
Expiry → Reminder → Renewal notifications.

Designed to degrade gracefully: if SMTP is not configured the service
logs the message it *would* have sent and reports "logged" instead of
failing. That means the reminder pipeline is fully testable and
demonstrable without a mail server, and turning on real delivery is
purely a configuration change.
"""
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from app.models.vendor import Vendor


def _smtp_configured() -> bool:
    return bool(
        getattr(settings, "smtp_host", "")
        and getattr(settings, "smtp_from", "")
    )


class EmailService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    # ── Delivery ──────────────────────────────────────────────
    def send(self, to: str, subject: str, body: str) -> dict:
        """Send one email. Returns {'status': 'sent'|'logged'|'failed'}."""
        if not to:
            return {"status": "failed", "reason": "no recipient"}

        if not _smtp_configured():
            logger.info(f"[email:logged] to={to} subject={subject!r}")
            logger.debug(f"[email:body]\n{body}")
            return {"status": "logged", "to": to, "subject": subject}

        try:
            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            port = int(getattr(settings, "smtp_port", 587) or 587)
            if getattr(settings, "smtp_use_ssl", False):
                server = smtplib.SMTP_SSL(settings.smtp_host, port, timeout=15)
            else:
                server = smtplib.SMTP(settings.smtp_host, port, timeout=15)
                if getattr(settings, "smtp_use_tls", True):
                    server.starttls()
            with server:
                user = getattr(settings, "smtp_user", "")
                pwd = getattr(settings, "smtp_password", "")
                if user and pwd:
                    server.login(user, pwd)
                server.send_message(msg)
            logger.info(f"[email:sent] to={to} subject={subject!r}")
            return {"status": "sent", "to": to, "subject": subject}
        except Exception as e:                     # never let email break a request
            logger.warning(f"[email:failed] to={to}: {e}")
            return {"status": "failed", "to": to, "reason": str(e)}

    # ── Templates ─────────────────────────────────────────────
    @staticmethod
    def expiry_reminder(vendor_name: str, coverage: str, expiry: str, days: int) -> tuple[str, str]:
        subject = f"Action needed: {coverage} expires in {days} day(s) — {vendor_name}"
        body = (
            f"Hello {vendor_name},\n\n"
            f"Our records show your {coverage} coverage expires on {expiry} "
            f"({days} day(s) from today).\n\n"
            "To remain compliant, please upload an updated certificate before the "
            "expiry date. You can do this from the Upload page in VendorClear AI.\n\n"
            "If you have already renewed, please disregard this message.\n\n"
            "— VendorClear AI Compliance"
        )
        return subject, body

    @staticmethod
    def expired_notice(vendor_name: str, coverage: str, expiry: str) -> tuple[str, str]:
        subject = f"Expired: {coverage} lapsed on {expiry} — {vendor_name}"
        body = (
            f"Hello {vendor_name},\n\n"
            f"Your {coverage} coverage expired on {expiry} and your account is now "
            "marked non-compliant. Work may be suspended until a valid certificate "
            "is on file.\n\n"
            "Please upload a renewed certificate as soon as possible.\n\n"
            "— VendorClear AI Compliance"
        )
        return subject, body

    @staticmethod
    def renewal_confirmation(vendor_name: str, coverage: str, new_expiry: str) -> tuple[str, str]:
        subject = f"Renewal confirmed: {coverage} valid to {new_expiry} — {vendor_name}"
        body = (
            f"Hello {vendor_name},\n\n"
            f"Thank you — we have processed your updated {coverage} certificate. "
            f"Your coverage is now recorded as valid through {new_expiry}.\n\n"
            "No further action is required.\n\n"
            "— VendorClear AI Compliance"
        )
        return subject, body

    # ── The reminder run ──────────────────────────────────────
    async def run_expiry_reminders(self, warning_days: int = 30) -> dict:
        """
        Scan vendors for coverage expiring within `warning_days` (or already
        expired) and send the appropriate notification. Returns a summary so
        the endpoint/scheduler can report what happened.
        """
        if self.db is None:
            return {"error": "no database session"}

        today = date.today()
        cutoff = today + timedelta(days=warning_days)
        results = {"reminders": 0, "expired_notices": 0, "skipped_no_email": 0, "details": []}

        vendors = list((await self.db.execute(
            select(Vendor).where(Vendor.is_active == True)  # noqa: E712
        )).scalars().all())

        for v in vendors:
            for coverage, expiry in (("General Liability", v.gl_expiry),
                                     ("Workers Compensation", v.wc_expiry)):
                if not expiry:
                    continue
                exp = expiry if isinstance(expiry, date) else date.fromisoformat(str(expiry)[:10])
                if exp > cutoff:
                    continue          # not due yet

                if not v.email:
                    results["skipped_no_email"] += 1
                    continue

                if exp < today:
                    subject, body = self.expired_notice(v.name, coverage, exp.isoformat())
                    results["expired_notices"] += 1
                else:
                    days = (exp - today).days
                    subject, body = self.expiry_reminder(v.name, coverage, exp.isoformat(), days)
                    results["reminders"] += 1

                outcome = self.send(v.email, subject, body)
                results["details"].append({
                    "vendor": v.name, "coverage": coverage,
                    "expiry": exp.isoformat(), "delivery": outcome["status"],
                })

        results["smtp_configured"] = _smtp_configured()
        return results
