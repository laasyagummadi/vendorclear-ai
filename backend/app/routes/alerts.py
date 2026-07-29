# ─────────────────────────────────────────────────────────────
#  app/routes/alerts.py  —  Compliance & expiry alerts (Nirupama)
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.notification_log import VendorNotificationLog, NotificationTrigger
from app.routes.auth import get_current_user_id
from app.services.compliance_service import ComplianceService
from app.services.notification_service import NotificationService
from app.utils.rbac import require_roles

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
)


@router.get("")
async def all_alerts(
    expiry_days: int = Query(default=30, ge=1, le=365, description="Look-ahead days for expiry alerts"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Combined alert feed:
    - Vendors with insurance expiring within `expiry_days`
    - Vendors with compliance issues (NON_COMPLIANT / NEEDS_REVIEW)
    """
    svc = ComplianceService(db)
    return await svc.get_all_alerts(expiry_days)


@router.get("/expiry")
async def expiry_alerts(
    days: int = Query(default=30, ge=1, le=365, description="Days ahead to scan for expiring coverage"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Vendors with GL or Workers Comp insurance expiring within `days` days.
    Sorted by days_until_expiry ascending (most urgent first).
    """
    svc = ComplianceService(db)
    return await svc.get_expiry_alerts(days)


@router.get("/compliance")
async def compliance_alerts(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Vendors flagged as NON_COMPLIANT or NEEDS_REVIEW.
    """
    svc = ComplianceService(db)
    return await svc.get_compliance_alerts()


@router.post("/notify")
async def notify_vendors(
    expiry_days: int = Query(default=30, ge=1, le=365, description="Look-ahead days for expiry alerts"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
):
    """
    Manually trigger vendor alert emails (the "Notify Vendors" button on the
    Alerts page). Emails every vendor with a new expiry/compliance item they
    haven't already been notified about at this urgency level — safe to
    click repeatedly, it won't re-send the same alert.
    """
    svc = NotificationService(db)
    return await svc.run(trigger=NotificationTrigger.MANUAL, expiry_days=expiry_days)


@router.get("/notifications")
async def notification_history(
    vendor_id: str | None = Query(default=None, description="Filter to a single vendor"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Recent vendor alert-email send history (audit trail)."""
    query = select(VendorNotificationLog).order_by(VendorNotificationLog.created_at.desc()).limit(limit)
    if vendor_id:
        query = query.where(VendorNotificationLog.vendor_id == vendor_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "vendor_id": log.vendor_id,
            "vendor_name": log.vendor.name if log.vendor else None,
            "trigger": log.trigger.value,
            "alert_type": log.alert_type,
            "coverage_type": log.coverage_type,
            "urgency_bucket": log.urgency_bucket,
            "recipient_email": log.recipient_email,
            "subject": log.subject,
            "success": log.success,
            "error_message": log.error_message,
            "sent_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
