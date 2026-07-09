# ─────────────────────────────────────────────────────────────
#  app/routes/alerts.py  —  Compliance & expiry alerts (Nirupama)
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.services.compliance_service import ComplianceService

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
