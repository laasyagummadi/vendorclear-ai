# ─────────────────────────────────────────────────────────────
#  app/services/compliance_service.py  —  Compliance engine (Nirupama)
# ─────────────────────────────────────────────────────────────
"""
VendorClear AI — Compliance Service
Computes compliance scores, risk assessments, and dashboard metrics.
Integrates with vendor, document, and analysis data.
"""
from datetime import date, datetime, timedelta
from typing import Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor, VendorStatus, RiskTier
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.analysis import Analysis, AnalysisStatus
from app.models.finding import Finding, FindingSeverity


# ── Compliance scoring weights ────────────────────────────────
WEIGHT_STATUS = 0.40        # 40 pts from vendor status
WEIGHT_DOCUMENTS = 0.30     # 30 pts from document completeness
WEIGHT_EXPIRY = 0.20        # 20 pts from insurance validity
WEIGHT_DIVERSITY = 0.10     # 10 pts from diversity certification

DAYS_EXPIRY_WARNING = 30    # alert if expiring within 30 days
DAYS_EXPIRY_CRITICAL = 7    # critical if expiring within 7 days


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Dashboard overview ───────────────────────────────────

    async def get_dashboard_summary(self) -> dict[str, Any]:
        """
        Aggregated stats for the main dashboard:
        - vendor counts by status
        - document counts by type/status
        - expiry alerts
        - recent activity
        - compliance rate trend (last 6 months placeholder)
        """
        today = date.today()

        # Vendor counts
        total_vendors = await self._count(Vendor, Vendor.is_active == True)
        compliant = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.status == VendorStatus.COMPLIANT)
        )
        needs_review = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.status == VendorStatus.NEEDS_REVIEW)
        )
        non_compliant = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.status == VendorStatus.NON_COMPLIANT)
        )

        # Risk tier breakdown
        low_risk = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.risk_tier == RiskTier.LOW)
        )
        medium_risk = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.risk_tier == RiskTier.MEDIUM)
        )
        high_risk = await self._count(
            Vendor, and_(Vendor.is_active == True, Vendor.risk_tier == RiskTier.HIGH)
        )

        # Document counts
        total_docs = await self._count(Document)
        processed_docs = await self._count(Document, Document.status == DocumentStatus.PROCESSED)
        pending_docs = await self._count(
            Document, Document.status.in_([DocumentStatus.PENDING, DocumentStatus.PROCESSING])
        )
        failed_docs = await self._count(Document, Document.status == DocumentStatus.FAILED)
        coi_docs = await self._count(Document, Document.document_type == DocumentType.COI)
        diversity_docs = await self._count(
            Document, Document.document_type == DocumentType.DIVERSITY_CERT
        )

        # Analysis verdict counts
        analysis_compliant = await self._count(
            Analysis, Analysis.status == AnalysisStatus.COMPLIANT
        )
        analysis_review = await self._count(
            Analysis, Analysis.status == AnalysisStatus.NEEDS_REVIEW
        )
        analysis_non_compliant = await self._count(
            Analysis, Analysis.status == AnalysisStatus.NON_COMPLIANT
        )

        # Expiry alerts (vendors with gl_expiry or wc_expiry within 30 days)
        expiring_soon = await self._get_expiring_vendors(days=DAYS_EXPIRY_WARNING)
        expiring_critical = await self._get_expiring_vendors(days=DAYS_EXPIRY_CRITICAL)

        # Compliance rate
        compliance_rate = round((compliant / total_vendors * 100), 1) if total_vendors > 0 else 0.0

        # Compliance-issue alert count (non-compliant + needs-review vendors)
        compliance_alert_count = needs_review + non_compliant

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "vendors": {
                "total": total_vendors,
                "active": total_vendors,  # all counted vendors are active (is_active=True filter)
                "compliant": compliant,
                "needs_review": needs_review,
                "non_compliant": non_compliant,
                "compliance_rate_pct": compliance_rate,
            },
            "risk_tiers": {
                "low": low_risk,
                "medium": medium_risk,
                "high": high_risk,
            },
            "documents": {
                "total": total_docs,
                "processed": processed_docs,
                "pending": pending_docs,
                "failed": failed_docs,
                "coi_count": coi_docs,
                "diversity_cert_count": diversity_docs,
            },
            "analyses": {
                "compliant": analysis_compliant,
                "needs_review": analysis_review,
                "non_compliant": analysis_non_compliant,
            },
            "alerts": {
                "total": len(expiring_soon) + compliance_alert_count,
                "expiry": len(expiring_soon),
                "compliance": compliance_alert_count,
                "expiring_within_30_days": len(expiring_soon),
                "expiring_within_7_days": len(expiring_critical),
            },
        }

    # ─── Alerts ───────────────────────────────────────────────

    async def get_expiry_alerts(self, days: int = DAYS_EXPIRY_WARNING) -> list[dict]:
        """Return vendors with insurance documents expiring within `days` days."""
        vendors = await self._get_expiring_vendors(days)
        today = date.today()
        alerts = []
        for v in vendors:
            for field, label in [("gl_expiry", "General Liability"), ("wc_expiry", "Workers Comp")]:
                expiry_str = getattr(v, field)
                if not expiry_str:
                    continue
                try:
                    exp = date.fromisoformat(expiry_str)
                    days_left = (exp - today).days
                    if 0 <= days_left <= days:
                        alerts.append({
                            "vendor_id": v.id,
                            "vendor_name": v.name,
                            "alert_type": "EXPIRING_SOON",
                            "coverage_type": label,
                            "expiry_date": expiry_str,
                            "days_until_expiry": days_left,
                            "severity": "CRITICAL" if days_left <= DAYS_EXPIRY_CRITICAL else "HIGH",
                        })
                except ValueError:
                    pass
        alerts.sort(key=lambda a: a["days_until_expiry"])
        return alerts

    async def get_compliance_alerts(self) -> list[dict]:
        """Return non-compliant and needs-review vendors as alerts."""
        result = await self.db.execute(
            select(Vendor)
            .where(
                and_(
                    Vendor.is_active == True,
                    Vendor.status != VendorStatus.COMPLIANT,
                )
            )
            .order_by(Vendor.status)
        )
        vendors = list(result.scalars().all())
        return [
            {
                "vendor_id": v.id,
                "vendor_name": v.name,
                "alert_type": "COMPLIANCE_ISSUE",
                "status": v.status.value,
                "risk_tier": v.risk_tier.value,
                "severity": "CRITICAL" if v.status == VendorStatus.NON_COMPLIANT else "HIGH",
            }
            for v in vendors
        ]

    async def get_all_alerts(self, expiry_days: int = DAYS_EXPIRY_WARNING) -> dict:
        """Combined alert feed."""
        expiry = await self.get_expiry_alerts(expiry_days)
        compliance = await self.get_compliance_alerts()
        return {
            "total": len(expiry) + len(compliance),
            "expiry_alerts": expiry,
            "compliance_alerts": compliance,
        }

    # ─── Vendor compliance score ──────────────────────────────

    async def compute_vendor_score(self, vendor_id: str) -> dict:
        """
        Calculate a 0-100 compliance score for a vendor.
        Breakdown:
          - Status score    (0-40)
          - Document score  (0-30)
          - Expiry score    (0-20)
          - Diversity score (0-10)
        """
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            return {"error": "Vendor not found"}

        today = date.today()

        # Status score
        status_scores = {
            VendorStatus.COMPLIANT: 40,
            VendorStatus.NEEDS_REVIEW: 20,
            VendorStatus.NON_COMPLIANT: 0,
        }
        status_score = status_scores.get(vendor.status, 0)

        # Document score — has at least one processed COI and one Diversity Cert
        docs_result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.vendor_id == vendor_id,
                    Document.status == DocumentStatus.PROCESSED,
                )
            )
        )
        docs = list(docs_result.scalars().all())
        has_coi = any(d.document_type == DocumentType.COI for d in docs)
        has_div = any(d.document_type == DocumentType.DIVERSITY_CERT for d in docs)
        doc_score = (15 if has_coi else 0) + (15 if has_div else 0)

        # Expiry score — check gl_expiry and wc_expiry
        expiry_score = 20
        for field in ["gl_expiry", "wc_expiry"]:
            val = getattr(vendor, field)
            if not val:
                expiry_score -= 5
                continue
            try:
                exp = date.fromisoformat(val)
                days_left = (exp - today).days
                if days_left < 0:
                    expiry_score -= 10
                elif days_left <= DAYS_EXPIRY_CRITICAL:
                    expiry_score -= 7
                elif days_left <= DAYS_EXPIRY_WARNING:
                    expiry_score -= 3
            except ValueError:
                expiry_score -= 5
        expiry_score = max(expiry_score, 0)

        # Diversity score
        div_types = vendor.diversity_types or []
        diversity_score = min(10, len(div_types) * 5) if div_types else 0

        total = status_score + doc_score + expiry_score + diversity_score
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "total_score": total,
            "breakdown": {
                "status_score": status_score,
                "document_score": doc_score,
                "expiry_score": expiry_score,
                "diversity_score": diversity_score,
            },
            "grade": _score_to_grade(total),
        }

    # ─── Reports ─────────────────────────────────────────────

    async def get_compliance_report(self) -> dict:
        """Full compliance report for all active vendors."""
        result = await self.db.execute(
            select(Vendor).where(Vendor.is_active == True)
        )
        vendors = list(result.scalars().all())

        report_rows = []
        for v in vendors:
            score_data = await self.compute_vendor_score(v.id)
            doc_count = await self._count(Document, Document.vendor_id == v.id)
            report_rows.append({
                "id": v.id,
                "name": v.name,
                "email": v.email,
                "status": v.status.value,
                "risk_tier": v.risk_tier.value,
                "total_score": score_data.get("total_score", 0),
                "grade": score_data.get("grade", "F"),
                "document_count": doc_count,
                "gl_expiry": v.gl_expiry,
                "wc_expiry": v.wc_expiry,
                "diversity_types": v.diversity_types or [],
            })

        report_rows.sort(key=lambda r: r["total_score"], reverse=True)

        # NOTE: previously this called self.get_dashboard_summary() in full
        # (13 extra COUNT queries) just to read summary["vendors"]. Compute
        # the handful of aggregates the report actually needs directly instead.
        total_vendors = len(vendors)
        compliant = sum(1 for v in vendors if v.status == VendorStatus.COMPLIANT)
        non_compliant = sum(1 for v in vendors if v.status == VendorStatus.NON_COMPLIANT)
        avg_score = (
            round(sum(r["total_score"] for r in report_rows) / total_vendors, 1)
            if total_vendors else 0.0
        )

        return {
            "report_date": date.today().isoformat(),
            "summary": {
                "total_vendors": total_vendors,
                "compliant": compliant,
                "non_compliant": non_compliant,
                "avg_score": avg_score,
            },
            "vendors": report_rows,
        }

    # ─── Helpers ──────────────────────────────────────────────

    async def _count(self, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for cond in conditions:
            stmt = stmt.where(cond)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_expiring_vendors(self, days: int) -> list[Vendor]:
        today = date.today()
        cutoff = (today + timedelta(days=days)).isoformat()
        today_str = today.isoformat()
        result = await self.db.execute(
            select(Vendor).where(
                and_(
                    Vendor.is_active == True,
                    Vendor.gl_expiry.isnot(None),
                    Vendor.gl_expiry >= today_str,
                    Vendor.gl_expiry <= cutoff,
                )
            )
        )
        gl_vendors = list(result.scalars().all())
        result2 = await self.db.execute(
            select(Vendor).where(
                and_(
                    Vendor.is_active == True,
                    Vendor.wc_expiry.isnot(None),
                    Vendor.wc_expiry >= today_str,
                    Vendor.wc_expiry <= cutoff,
                )
            )
        )
        wc_vendors = list(result2.scalars().all())
        # Deduplicate
        seen = set()
        all_vendors = []
        for v in gl_vendors + wc_vendors:
            if v.id not in seen:
                seen.add(v.id)
                all_vendors.append(v)
        return all_vendors


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"
