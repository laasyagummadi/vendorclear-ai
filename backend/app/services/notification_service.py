# ─────────────────────────────────────────────────────────────
#  app/services/notification_service.py  —  Vendor alert emails
# ─────────────────────────────────────────────────────────────
"""
Turns the existing alert feed (ComplianceService.get_all_alerts) into
actual emails sent to vendors, at the address they've given us
(Vendor.email).

Design:
  - One email per vendor per run, listing every *new* item they need to
    know about (not one email per alert row) — a vendor with 3 expiring
    certs gets a single email, not 3.
  - "New" means: this specific alert has moved into an urgency tier
    (30/14/7/3/1 days / OVERDUE, or a compliance status) that we haven't
    already emailed them about. This is what keeps the daily scheduled
    job from re-sending the same email every single day — a vendor only
    gets re-notified as the situation actually gets more urgent.
  - Every send attempt (success or failure) is recorded in
    VendorNotificationLog for audit + dedupe.
  - Vendors with no email on file are skipped and reported back, so the
    caller (API response / logs) can surface "these vendors couldn't be
    reached" rather than failing silently.
"""
from datetime import date
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.vendor import Vendor
from app.models.notification_log import (
    VendorNotificationLog, NotificationChannel, NotificationTrigger,
)
from app.services.compliance_service import ComplianceService
from app.services.email_service import email_service

URGENCY_THRESHOLDS = [1, 3, 7, 14, 30]


def _expiry_urgency_bucket(days_until_expiry: int) -> str:
    if days_until_expiry < 0:
        return "OVERDUE"
    for t in URGENCY_THRESHOLDS:
        if days_until_expiry <= t:
            return str(t)
    return "30"


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compliance_service = ComplianceService(db)

    async def _already_notified(
        self, vendor_id: str, alert_type: str, coverage_type: str | None,
        expiry_date: str | None, urgency_bucket: str,
    ) -> bool:
        result = await self.db.execute(
            select(VendorNotificationLog.id).where(
                and_(
                    VendorNotificationLog.vendor_id == vendor_id,
                    VendorNotificationLog.alert_type == alert_type,
                    VendorNotificationLog.coverage_type == coverage_type,
                    VendorNotificationLog.expiry_date == expiry_date,
                    VendorNotificationLog.urgency_bucket == urgency_bucket,
                    VendorNotificationLog.success == True,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _new_items_for_vendor(self, expiry_alerts: list[dict], compliance_alerts: list[dict]) -> dict[str, list[dict]]:
        """Group not-yet-notified alert items by vendor_id."""
        by_vendor: dict[str, list[dict]] = {}

        for a in expiry_alerts:
            bucket = _expiry_urgency_bucket(a["days_until_expiry"])
            if await self._already_notified(
                a["vendor_id"], a["alert_type"], a.get("coverage_type"), a.get("expiry_date"), bucket
            ):
                continue
            item = dict(a)
            item["urgency_bucket"] = bucket
            by_vendor.setdefault(a["vendor_id"], []).append(item)

        for a in compliance_alerts:
            bucket = a["status"]
            if await self._already_notified(a["vendor_id"], a["alert_type"], None, None, bucket):
                continue
            item = dict(a)
            item["urgency_bucket"] = bucket
            item["coverage_type"] = None
            item["expiry_date"] = None
            by_vendor.setdefault(a["vendor_id"], []).append(item)

        return by_vendor

    def _compose_email(self, vendor_name: str, items: list[dict]) -> tuple[str, str, str]:
        """Returns (subject, html_body, text_body)."""
        expiry_items = [i for i in items if i["alert_type"] != "COMPLIANCE_ISSUE"]
        compliance_items = [i for i in items if i["alert_type"] == "COMPLIANCE_ISSUE"]

        most_urgent = "OVERDUE" if any(i["urgency_bucket"] == "OVERDUE" for i in expiry_items) else None
        if most_urgent or compliance_items:
            subject = f"Action required: compliance alert for {vendor_name}"
        else:
            subject = f"Upcoming compliance deadline for {vendor_name}"

        lines_html = []
        lines_text = []
        for i in expiry_items:
            if i["urgency_bucket"] == "OVERDUE":
                desc = f"{i['coverage_type']} coverage EXPIRED on {i['expiry_date']} (overdue by {i['days_overdue']} days)"
            else:
                desc = f"{i['coverage_type']} coverage expires on {i['expiry_date']} ({i['days_until_expiry']} days from now)"
            lines_html.append(f"<li>{desc}</li>")
            lines_text.append(f"- {desc}")

        for i in compliance_items:
            desc = f"Your account has been flagged as {i['status'].replace('_', ' ').title()}. Please review and provide any outstanding documentation."
            lines_html.append(f"<li>{desc}</li>")
            lines_text.append(f"- {desc}")

        html_body = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; color: #222;">
          <p>Hello {vendor_name},</p>
          <p>This is an automated notice from VendorClear AI regarding your vendor compliance record:</p>
          <ul>
            {''.join(lines_html)}
          </ul>
          <p>Please log in to the vendor portal or contact your assigned analyst to resolve these items as soon as possible.</p>
          <p style="color:#888; font-size:12px;">This is an automated compliance notification. Please do not reply directly to this email.</p>
        </div>
        """
        text_body = (
            f"Hello {vendor_name},\n\n"
            "This is an automated notice from VendorClear AI regarding your vendor compliance record:\n\n"
            + "\n".join(lines_text)
            + "\n\nPlease log in to the vendor portal or contact your assigned analyst to resolve these items as soon as possible.\n"
            "\n(This is an automated compliance notification. Please do not reply directly to this email.)"
        )
        return subject, html_body, text_body

    async def run(self, trigger: NotificationTrigger, expiry_days: int = 30) -> dict[str, Any]:
        """Scan alerts, email every vendor with a new (not-yet-notified) item.
        Returns a summary dict suitable for an API response or log line."""
        if not email_service.is_enabled():
            if email_service.has_placeholder_credentials():
                reason = (
                    "Alert emails are configured with placeholder Mailtrap credentials from "
                    ".env.example — swap in your real SMTP_USER/SMTP_PASSWORD from your own "
                    "Mailtrap (or other provider) inbox in .env, then try again."
                )
            else:
                reason = (
                    "Alert emails are disabled — set ALERTS_EMAIL_ENABLED=true and configure "
                    "SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env."
                )
            return {
                "sent": 0,
                "skipped_no_email": 0,
                "failed": 0,
                "disabled_reason": reason,
            }

        alerts = await self.compliance_service.get_all_alerts(expiry_days)
        by_vendor = await self._new_items_for_vendor(alerts["expiry_alerts"], alerts["compliance_alerts"])

        sent, skipped_no_email, failed = 0, 0, 0
        notified_vendor_names: list[str] = []
        skipped_vendor_names: list[str] = []

        for vendor_id, items in by_vendor.items():
            vendor = await self.db.get(Vendor, vendor_id)
            if not vendor:
                continue
            if not vendor.email:
                skipped_no_email += 1
                skipped_vendor_names.append(vendor.name)
                continue

            subject, html_body, text_body = self._compose_email(vendor.name, items)
            try:
                await email_service.send_email(vendor.email, subject, html_body, text_body)
                success, error_message = True, None
                sent += 1
                notified_vendor_names.append(vendor.name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(f"Failed to send alert email to vendor {vendor_id}: {exc}")
                success, error_message = False, str(exc)
                failed += 1

            for item in items:
                self.db.add(VendorNotificationLog(
                    vendor_id=vendor_id,
                    channel=NotificationChannel.EMAIL,
                    trigger=trigger,
                    alert_type=item["alert_type"],
                    coverage_type=item.get("coverage_type"),
                    expiry_date=item.get("expiry_date"),
                    urgency_bucket=item["urgency_bucket"],
                    recipient_email=vendor.email,
                    subject=subject,
                    success=success,
                    error_message=error_message,
                ))
            await self.db.flush()

        await self.db.commit()

        return {
            "sent": sent,
            "skipped_no_email": skipped_no_email,
            "failed": failed,
            "notified_vendors": notified_vendor_names,
            "skipped_vendors": skipped_vendor_names,
        }
