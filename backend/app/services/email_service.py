# ─────────────────────────────────────────────────────────────
#  app/services/email_service.py  —  Unified Email Service
# ─────────────────────────────────────────────────────────────
"""
Thin wrapper around a generic SMTP server (Gmail, Outlook/Office365, Mailtrap, etc)
for sending vendor-facing reminder and alert emails.
"""
from datetime import date, timedelta
from email.message import EmailMessage
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiosmtplib

from config import settings
from app.models.vendor import Vendor


# The exact example values shipped in .env.example / the .env comment block
_PLACEHOLDER_SMTP_USERS = {"1a2b3c4d5e6f7g"}
_PLACEHOLDER_SMTP_PASSWORDS = {"9h8i7j6k5l4m3n"}


class EmailNotConfiguredError(Exception):
    """Raised when a send is attempted but SMTP hasn't been configured."""


class EmailService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    def has_placeholder_credentials(self) -> bool:
        """True if SMTP_USER/SMTP_PASSWORD are still the example placeholders."""
        return (
            settings.smtp_user in _PLACEHOLDER_SMTP_USERS
            or settings.smtp_password in _PLACEHOLDER_SMTP_PASSWORDS
        )

    def is_configured(self) -> bool:
        return (
            bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)
            and not self.has_placeholder_credentials()
        )

    def is_enabled(self) -> bool:
        return settings.alerts_email_enabled and self.is_configured()

    async def send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> None:
        """Send a single email asynchronously. Raises on failure."""
        if self.has_placeholder_credentials():
            raise EmailNotConfiguredError(
                "SMTP_USER/SMTP_PASSWORD are still the placeholder example values from .env.example"
            )
        if not self.is_configured():
            raise EmailNotConfiguredError(
                "SMTP is not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env"
            )

        from_email = settings.smtp_from_email or settings.smtp_user

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=settings.smtp_use_tls,
            timeout=15,
        )
        logger.info(f"Alert email sent to {to_email}: {subject}")

    async def send(self, to: str, subject: str, body: str) -> dict:
        """Send one email. If not configured, logs to stdout instead of failing."""
        if not to:
            return {"status": "failed", "reason": "no recipient"}

        if not self.is_configured():
            logger.info(f"[email:logged] to={to} subject={subject!r}")
            logger.debug(f"[email:body]\n{body}")
            return {"status": "logged", "to": to, "subject": subject}

        try:
            html_body = f"<p>{body.replace(chr(10), '<br>')}</p>"
            await self.send_email(to, subject, html_body, body)
            return {"status": "sent", "to": to, "subject": subject}
        except Exception as e:
            logger.warning(f"[email:failed] to={to}: {e}")
            return {"status": "failed", "to": to, "reason": str(e)}

    # ── Templates (from LIGHT) ──────────────────────────────────
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

    # ── The reminder run (from LIGHT) ───────────────────────────
    async def run_expiry_reminders(self, warning_days: int = 30) -> dict:
        """
        Scan vendors for coverage expiring within `warning_days` (or already
        expired) and send the appropriate notification.
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
                    continue

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

                outcome = await self.send(v.email, subject, body)
                results["details"].append({
                    "vendor": v.name, "coverage": coverage,
                    "expiry": exp.isoformat(), "delivery": outcome["status"],
                })

        results["smtp_configured"] = self.is_configured()
        return results


# Global singleton instance for notification_service.py
email_service = EmailService()
