# ─────────────────────────────────────────────────────────────
#  app/models/notification_log.py  —  Vendor alert email log
# ─────────────────────────────────────────────────────────────
"""
Records every vendor-facing alert email that has been sent (or attempted),
so:
  1. Vendors aren't re-emailed every single day for the same expiring
     certificate — we only re-notify when the urgency tier changes
     (e.g. "expiring in 30 days" -> "expiring in 7 days" -> "overdue").
  2. There's an audit trail admins/analysts can inspect: who was notified,
     when, about what, and whether the send succeeded.
"""
import enum
from typing import Optional

from sqlalchemy import String, Boolean, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"


class NotificationTrigger(str, enum.Enum):
    SCHEDULED = "SCHEDULED"   # sent by the daily background job
    MANUAL = "MANUAL"         # sent by an admin/analyst clicking "Notify Vendors"


class VendorNotificationLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vendor_notification_logs"

    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor: Mapped["Vendor"] = relationship("Vendor", lazy="selectin")  # noqa: F821

    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel), default=NotificationChannel.EMAIL, nullable=False
    )
    trigger: Mapped[NotificationTrigger] = mapped_column(
        SAEnum(NotificationTrigger), nullable=False, index=True
    )

    # What this email was about, e.g. "General Liability" / "Workers Comp" /
    # "COMPLIANCE_ISSUE". Used together with urgency_bucket to build the
    # dedupe key (see notification_service.py).
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Urgency tier at time of send: 30 / 14 / 7 / 3 / 1 / OVERDUE / COMPLIANCE.
    # Re-notification happens when a vendor moves into a *new* tier, not on
    # every scheduler run.
    urgency_bucket: Mapped[str] = mapped_column(String(20), nullable=False)

    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<VendorNotificationLog vendor={self.vendor_id} bucket={self.urgency_bucket} ok={self.success}>"
