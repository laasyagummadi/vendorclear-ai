# ─────────────────────────────────────────────────────────────
#  app/routes/dashboard.py  —  Dashboard & reporting (Nirupama)
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.services.compliance_service import ComplianceService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get("/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Full dashboard overview:
    - vendor counts by status
    - risk tier breakdown
    - document and analysis stats
    - active alert counts
    """
    svc = ComplianceService(db)
    return await svc.get_dashboard_summary()


@router.get("/compliance-report")
async def compliance_report(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Full compliance report across all active vendors, sorted by score descending."""
    svc = ComplianceService(db)
    return await svc.get_compliance_report()


@router.get("/vendors/{vendor_id}/score")
async def vendor_compliance_score(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Compute a 0–100 compliance score with breakdown for a single vendor."""
    svc = ComplianceService(db)
    return await svc.compute_vendor_score(vendor_id)
