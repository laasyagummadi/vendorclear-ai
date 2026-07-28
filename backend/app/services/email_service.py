# ─────────────────────────────────────────────────────────────
#  app/services/email_service.py  —  Outbound email (vendor alerts)
# ─────────────────────────────────────────────────────────────
"""
Thin wrapper around a generic SMTP server (Gmail, Outlook/Office365, Zoho,
a corporate relay, etc) for sending vendor-facing alert emails.

Configuration lives in config.py / .env (SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASSWORD, SMTP_USE_TLS, SMTP_FROM_EMAIL, SMTP_FROM_NAME).

If ALERTS_EMAIL_ENABLED is false, or SMTP_HOST/SMTP_USER aren't set, sends
are skipped (logged, not raised) so the rest of the app keeps working
without email configured.
"""
from email.message import EmailMessage
from loguru import logger

import aiosmtplib

from config import settings


# The exact example values shipped in .env.example / the .env comment block
# ("EXAMPLE VALUES BELOW (Mailtrap sandbox)"). These are non-functional
# placeholders — if they're still in place, every send will fail SMTP auth,
# which otherwise shows up as a confusing per-vendor "Failed" in the
# notification log instead of a clear "not actually configured" message.
_PLACEHOLDER_SMTP_USERS = {"1a2b3c4d5e6f7g"}
_PLACEHOLDER_SMTP_PASSWORDS = {"9h8i7j6k5l4m3n"}


class EmailNotConfiguredError(Exception):
    """Raised when a send is attempted but SMTP hasn't been configured."""


class EmailService:
    def has_placeholder_credentials(self) -> bool:
        """True if SMTP_USER/SMTP_PASSWORD are still the example placeholders
        shipped in .env.example rather than real Mailtrap (or other provider)
        credentials."""
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
        """Send a single email. Raises on failure so callers can log it
        per-recipient rather than have one bad send silently swallowed."""
        if self.has_placeholder_credentials():
            raise EmailNotConfiguredError(
                "SMTP_USER/SMTP_PASSWORD are still the placeholder example values from "
                ".env.example — replace them with your real Mailtrap (or other provider) "
                "credentials in .env, then set ALERTS_EMAIL_ENABLED=true."
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
            timeout=15,  # fail fast on a bad host/port instead of hanging the request
        )
        logger.info(f"Alert email sent to {to_email}: {subject}")


email_service = EmailService()
