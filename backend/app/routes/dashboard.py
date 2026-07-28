# ─────────────────────────────────────────────────────────────
#  app/routes/dashboard.py  —  Dashboard & reporting (Nirupama)
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id, get_current_user
from app.services.compliance_service import ComplianceService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get("/me")
async def role_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Module 5 — Role Based Dashboards.

    Returns a homepage payload shaped for the caller's role:
      ADMIN   → full org overview + configuration snapshot
      ANALYST → operational overview (vendors, docs, alerts) without config control
      VENDOR  → only their own vendor record, settings and documents
      AUDITOR → read-only compliance posture across the org
    """
    from app.utils.permissions import role_of, permissions_for
    from app.models.user import UserRole
    from app.models.vendor import Vendor
    from app.services.config_service import ConfigService

    role = role_of(current_user)
    svc = ComplianceService(db)
    payload: dict = {
        "role": role.value,
        "permissions": permissions_for(current_user),
        "user": {"id": current_user.id, "name": current_user.full_name},
    }

    # ── VENDOR: strictly their own data ───────────────────────
    if role == UserRole.VENDOR:
        payload["view"] = "vendor"
        vendor = await db.get(Vendor, current_user.vendor_id) if current_user.vendor_id else None
        if not vendor:
            payload["vendor"] = None
            payload["message"] = "No vendor record is linked to this account yet."
            return payload
        cfg = await ConfigService(db).get_effective_config(vendor)
        score = await svc.compute_vendor_score(vendor.id)
        payload["vendor"] = {
            "id": vendor.id,
            "name": vendor.name,
            "status": vendor.status.value if vendor.status else None,
            "risk_tier": vendor.risk_tier.value if vendor.risk_tier else None,
            "gl_expiry": vendor.gl_expiry,
            "wc_expiry": vendor.wc_expiry,
            "assigned_version": vendor.assigned_version,
        }
        payload["my_settings"] = cfg
        payload["my_score"] = score
        return payload

    # ── Everyone else gets the org-wide summary ───────────────
    summary = await svc.get_dashboard_summary()
    payload["summary"] = summary

    if role == UserRole.ADMIN:
        payload["view"] = "admin"
        payload["config"] = await ConfigService(db).get_all_configs()
    elif role == UserRole.ANALYST:
        payload["view"] = "analyst"
        payload["report"] = await svc.get_compliance_report()
    elif role == UserRole.AUDITOR:
        payload["view"] = "auditor"
        payload["report"] = await svc.get_compliance_report()
        payload["read_only"] = True

    return payload


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
