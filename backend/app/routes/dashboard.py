# ─────────────────────────────────────────────────────────────
#  app/routes/dashboard.py  —  Dashboard & reporting (Nirupama)
# ─────────────────────────────────────────────────────────────
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.utils.rbac import get_current_user
from app.services.compliance_service import ComplianceService
from app.models.vendor import VendorStatus, RiskTier, VendorCategory, VendorType
from app.models.document import DocumentType

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


def _report_filters(
    status_filter: Optional[VendorStatus] = Query(None, alias="status"),
    risk_tier: Optional[RiskTier] = Query(None),
    category: Optional[VendorCategory] = Query(None),
    vendor_type: Optional[VendorType] = Query(None),
    business_unit: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    insurance_provider: Optional[str] = Query(None),
    assigned_analyst: Optional[str] = Query(None, description="Analyst full name (partial match)"),
    document_type: Optional[DocumentType] = Query(None),
    expiry_before: Optional[str] = Query(None, description="ISO date — GL or WC expiry on/before this date"),
    search: Optional[str] = Query(None),
) -> dict:
    return {
        "status": status_filter,
        "risk_tier": risk_tier,
        "category": category,
        "vendor_type": vendor_type,
        "business_unit": business_unit,
        "region": region,
        "insurance_provider": insurance_provider,
        "assigned_analyst": assigned_analyst,
        "document_type": document_type,
        "expiry_before": expiry_before,
        "search": search,
    }


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
    filters: dict = Depends(_report_filters),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Compliance report across active vendors (sorted by risk/status/score),
    optionally narrowed by status, risk_tier, category, business_unit, region, or search."""
    svc = ComplianceService(db)
    return await svc.get_compliance_report(filters)


@router.get("/compliance-report/export")
async def compliance_report_export(
    filters: dict = Depends(_report_filters),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Export the (optionally filtered) compliance report as a CSV download."""
    svc = ComplianceService(db)
    report = await svc.get_compliance_report(filters)

    buf = io.StringIO()
    fieldnames = [
        "id", "name", "email", "category", "vendor_type", "business_unit", "region",
        "insurance_provider", "assigned_analyst",
        "status", "risk_tier", "total_score", "grade", "health",
        "document_count", "gl_expiry", "wc_expiry", "diversity_types",
        "priority", "expiry_flag",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in report["vendors"]:
        row = dict(row)
        row["diversity_types"] = ",".join(row.get("diversity_types") or [])
        writer.writerow(row)
    buf.seek(0)

    filename = f"compliance-report-{report['report_date']}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/vendors/{vendor_id}/score")
async def vendor_compliance_score(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Compute a 0–100 compliance score with breakdown for a single vendor."""
    svc = ComplianceService(db)
    return await svc.compute_vendor_score(vendor_id)


@router.get("/health-overview")
async def fleet_health_overview(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Fleet-wide vendor health score (Feature 17): average score, overall
    grade, and per-grade distribution across all active vendors.
    """
    svc = ComplianceService(db)
    return await svc.get_fleet_health_score()


@router.get("/vendors/{vendor_id}/timeline")
async def vendor_timeline(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Chronological lifecycle timeline for a single vendor (Module 8):
    Vendor Created -> Insurance Uploaded -> AI Analysis Completed ->
    Manual Review -> Approved -> Reminder Sent -> Renewed.
    """
    svc = ComplianceService(db)
    return await svc.get_vendor_timeline(vendor_id)


@router.get("/analytics")
async def analytics(
    months: int = Query(default=6, ge=1, le=24, description="Number of months of onboarding-cohort trend to include"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Business-intelligence analytics (Module 9): monthly compliance trend,
    regional analysis, risk distribution (fleet-wide and by category), and
    the most common compliance violations across all active vendors.
    """
    svc = ComplianceService(db)
    return await svc.get_analytics(months)
