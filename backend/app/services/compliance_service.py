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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor, VendorStatus, RiskTier, VendorCategory
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.analysis import Analysis, AnalysisStatus
from app.models.finding import Finding, FindingSeverity
from app.models.policy import CompliancePolicy
from app.models.user import User
from app.models.notification_log import VendorNotificationLog

DAYS_EXPIRY_WARNING = 60    # alert if expiring within 60 days
DAYS_EXPIRY_CRITICAL = 7    # critical if expiring within 7 days
DAYS_ESCALATION = 3         # escalate (bump to top, notify) if expiring within 3 days or already overdue

# ── Fallback scoring weights ────────────────────────────────
# Used ONLY when no CompliancePolicy row exists yet for a vendor's
# category (e.g. right after a fresh deploy, before an admin has
# configured policies). Every vendor used to get these same weights
# unconditionally — now they're purely a bootstrap default; per-category
# policies (Construction / Software / Electrical / Other), configurable
# via /api/v1/policies, take over as soon as they exist.
DEFAULT_WEIGHT_STATUS = 0.40
DEFAULT_WEIGHT_DOCUMENTS = 0.30
DEFAULT_WEIGHT_EXPIRY = 0.20
DEFAULT_WEIGHT_DIVERSITY = 0.10
DEFAULT_PENALTY_CRITICAL = 10.0
DEFAULT_PENALTY_HIGH = 5.0
DEFAULT_PENALTY_MEDIUM = 2.0
DEFAULT_RISK_LOW_MIN = 75.0
DEFAULT_RISK_MEDIUM_MIN = 50.0


class _DefaultPolicy:
    """Drop-in stand-in for a CompliancePolicy row, used when a vendor's
    category has no admin-configured policy yet."""
    weight_status = DEFAULT_WEIGHT_STATUS
    weight_documents = DEFAULT_WEIGHT_DOCUMENTS
    weight_expiry = DEFAULT_WEIGHT_EXPIRY
    weight_diversity = DEFAULT_WEIGHT_DIVERSITY
    finding_penalty_critical = DEFAULT_PENALTY_CRITICAL
    finding_penalty_high = DEFAULT_PENALTY_HIGH
    finding_penalty_medium = DEFAULT_PENALTY_MEDIUM
    required_document_types = None
    risk_low_min_score = DEFAULT_RISK_LOW_MIN
    risk_medium_min_score = DEFAULT_RISK_MEDIUM_MIN
    category = None
    name = "Default (unconfigured)"


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
        # Escalation-window expiries (Module 10 — includes already-overdue coverage)
        expiring_escalated = await self._get_expiring_vendors(days=DAYS_ESCALATION, include_overdue=True)

        # Compliance rate
        compliance_rate = round((compliant / total_vendors * 100), 1) if total_vendors > 0 else 0.0

        # Compliance-issue alert count (non-compliant + needs-review vendors)
        compliance_alert_count = needs_review + non_compliant
        # Escalated compliance issues: NON_COMPLIANT stacked with HIGH risk —
        # the two worst signals together, same rule used in get_compliance_alerts().
        escalated_compliance_count = await self._count(
            Vendor,
            and_(
                Vendor.is_active == True,
                Vendor.status == VendorStatus.NON_COMPLIANT,
                Vendor.risk_tier == RiskTier.HIGH,
            ),
        )
        escalated_count = len(expiring_escalated) + escalated_compliance_count

        # Fleet-wide vendor health score (Feature 17 rollup for dashboard)
        try:
            health = await self.get_fleet_health_score()
        except Exception as exc:  # pragma: no cover - defensive guard
            import logging
            logging.getLogger(__name__).exception(
                "get_fleet_health_score() failed while building dashboard summary: %s", exc
            )
            health = {
                "avg_score": 0.0,
                "grade": "N/A",
                "vendor_count": 0,
                "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                "error": str(exc),
            }

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
                "escalated_count": escalated_count,
            },
            "health": health,
        }

    # ─── Alerts ───────────────────────────────────────────────

    async def get_expiry_alerts(self, days: int = DAYS_EXPIRY_WARNING) -> list[dict]:
        """Return vendors with insurance coverage expiring within `days` days,
        plus coverage that has ALREADY expired (previously silently ignored —
        an overdue GL/WC certificate is the single most urgent alert case and
        needs a `days_until_expiry` of 0 or less rather than dropping off the
        list once the expiry date passes)."""
        vendors = await self._get_expiring_vendors(days, include_overdue=True)
        today = date.today()
        alerts = []
        for v in vendors:
            for field, label in [("gl_expiry", "General Liability"), ("wc_expiry", "Workers Comp")]:
                expiry_str = getattr(v, field)
                if not expiry_str:
                    continue
                try:
                    exp = date.fromisoformat(expiry_str)
                except ValueError:
                    continue
                days_left = (exp - today).days
                if days_left > days:
                    continue
                overdue = days_left < 0
                priority, escalated = _expiry_priority(days_left)
                alerts.append({
                    "vendor_id": v.id,
                    "vendor_name": v.name,
                    "alert_type": "OVERDUE" if overdue else "EXPIRING_SOON",
                    "coverage_type": label,
                    "expiry_date": expiry_str,
                    "days_until_expiry": days_left,
                    "days_overdue": abs(days_left) if overdue else 0,
                    "severity": "CRITICAL" if days_left <= DAYS_EXPIRY_CRITICAL else "HIGH",
                    "priority": priority,
                    "escalated": escalated,
                })
        # Most urgent first: overdue/soonest-expiring at the top.
        alerts.sort(key=lambda a: a["days_until_expiry"])
        return alerts

    async def get_compliance_alerts(self) -> list[dict]:
        """Return non-compliant and needs-review vendors as alerts, each with
        a priority tier and an escalation flag so the UI/notifications can
        surface the vendors that most urgently need analyst attention."""
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
        alerts = []
        for v in vendors:
            non_compliant = v.status == VendorStatus.NON_COMPLIANT
            priority = "CRITICAL" if non_compliant else "HIGH"
            # Escalate a NON_COMPLIANT + HIGH-risk vendor combination — the
            # two worst signals stacking is what should page an admin rather
            # than just sit in an analyst's queue.
            escalated = non_compliant and v.risk_tier == RiskTier.HIGH
            alerts.append({
                "vendor_id": v.id,
                "vendor_name": v.name,
                "alert_type": "COMPLIANCE_ISSUE",
                "status": v.status.value,
                "risk_tier": v.risk_tier.value,
                "severity": "CRITICAL" if non_compliant else "HIGH",
                "priority": priority,
                "escalated": escalated,
            })
        # CRITICAL+escalated first, then CRITICAL, then HIGH.
        alerts.sort(key=lambda a: (0 if a["escalated"] else 1, 0 if a["priority"] == "CRITICAL" else 1))
        return alerts

    async def get_all_alerts(self, expiry_days: int = DAYS_EXPIRY_WARNING) -> dict:
        """Combined alert feed, with an `escalated_count` so the dashboard/
        sidebar can surface how many alerts need immediate attention rather
        than just a flat total."""
        expiry = await self.get_expiry_alerts(expiry_days)
        compliance = await self.get_compliance_alerts()
        escalated_count = sum(1 for a in expiry if a["escalated"]) + sum(1 for a in compliance if a["escalated"])
        return {
            "total": len(expiry) + len(compliance),
            "escalated_count": escalated_count,
            "expiry_alerts": expiry,
            "compliance_alerts": compliance,
        }

    # ─── Vendor compliance score ──────────────────────────────

    async def get_policy_for_category(self, category) -> "CompliancePolicy | _DefaultPolicy":
        """Look up the admin-configured policy for a vendor's category.
        Falls back to the bootstrap default if none has been configured yet
        (e.g. right after a fresh deploy, before an admin visits /policies)."""
        if category is not None:
            result = await self.db.execute(
                select(CompliancePolicy).where(
                    CompliancePolicy.category == category,
                    CompliancePolicy.is_active == True,
                )
            )
            policy = result.scalar_one_or_none()
            if policy:
                return policy
        return _DefaultPolicy()

    async def compute_vendor_score(self, vendor_id: str) -> dict:
        """
        Calculate a 0-100 compliance score for a vendor, using the
        admin-configurable CompliancePolicy that matches the vendor's
        category (Construction / Software / Electrical / Other) rather
        than one fixed weighting applied to every vendor.

        Breakdown (each sub-score is 0-100, then combined by the policy's
        weights, which are normalized to sum to 1.0):
          - Status score
          - Document score (required document types come from the policy)
          - Expiry score
          - Diversity score
          - Finding penalty (policy-defined per-severity point deductions)

        risk_tier is derived from the resulting score against the policy's
        thresholds and persisted onto the vendor — it's no longer a
        manually-set static field.
        """
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            return {"error": "Vendor not found"}

        policy = await self.get_policy_for_category(vendor.category)

        # Finding has no direct vendor_id column — it links to a vendor via
        # Finding.analysis_id -> Analysis.document_id -> Document.vendor_id.
        findings_result = await self.db.execute(
            select(Finding)
            .join(Analysis, Finding.analysis_id == Analysis.id)
            .join(Document, Analysis.document_id == Document.id)
            .where(Document.vendor_id == vendor_id)
        )
        findings = findings_result.scalars().all()

        finding_penalty = 0.0
        for finding in findings:
            if finding.severity == FindingSeverity.CRITICAL:
                finding_penalty += policy.finding_penalty_critical
            elif finding.severity == FindingSeverity.HIGH:
                finding_penalty += policy.finding_penalty_high
            elif finding.severity == FindingSeverity.MEDIUM:
                finding_penalty += policy.finding_penalty_medium

        today = date.today()

        # ── Status sub-score (0-100) ────────────────────────────
        status_subscores = {
            VendorStatus.COMPLIANT: 100,
            VendorStatus.NEEDS_REVIEW: 50,
            VendorStatus.NON_COMPLIANT: 0,
        }
        status_subscore = status_subscores.get(vendor.status, 0)

        # ── Document sub-score (0-100) ───────────────────────────
        # Required document types come from the policy (defaults to
        # COI + Diversity Cert, same as before, if the policy doesn't
        # specify its own list — e.g. a Software policy might only
        # require a COI).
        required_types = policy.required_document_types or [
            DocumentType.COI.value, DocumentType.DIVERSITY_CERT.value
        ]
        docs_result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.vendor_id == vendor_id,
                    Document.status == DocumentStatus.PROCESSED,
                )
            )
        )
        docs = list(docs_result.scalars().all())
        present_types = {d.document_type.value for d in docs}
        matched = sum(1 for t in required_types if t in present_types)
        doc_subscore = round((matched / len(required_types)) * 100) if required_types else 100

        # ── Expiry sub-score (0-100) ─────────────────────────────
        expiry_subscore = 100
        for field in ["gl_expiry", "wc_expiry"]:
            val = getattr(vendor, field)
            if not val:
                expiry_subscore -= 25
                continue
            try:
                exp = date.fromisoformat(val)
                days_left = (exp - today).days
                if days_left < 0:
                    expiry_subscore -= 50
                elif days_left <= DAYS_EXPIRY_CRITICAL:
                    expiry_subscore -= 35
                elif days_left <= DAYS_EXPIRY_WARNING:
                    expiry_subscore -= 15
            except ValueError:
                expiry_subscore -= 25
        expiry_subscore = max(expiry_subscore, 0)

        # ── Diversity sub-score (0-100) ──────────────────────────
        div_types = vendor.diversity_types or []
        diversity_subscore = min(100, len(div_types) * 50) if div_types else 0

        # ── Combine via policy weights, normalized so a misconfigured
        # policy (weights not summing to 1.0) can't silently over/under
        # score every vendor in that category. ────────────────────────
        raw_weights = [
            policy.weight_status, policy.weight_documents,
            policy.weight_expiry, policy.weight_diversity,
        ]
        weight_total = sum(raw_weights) or 1.0
        w_status, w_docs, w_expiry, w_div = [w / weight_total for w in raw_weights]

        weighted_total = (
            status_subscore * w_status
            + doc_subscore * w_docs
            + expiry_subscore * w_expiry
            + diversity_subscore * w_div
        )
        total = round(weighted_total - finding_penalty)
        total = max(0, min(100, total))

        if total >= 90:
            health = "Excellent"
        elif total >= 75:
            health = "Good"
        elif total >= 60:
            health = "Fair"
        elif total >= 40:
            health = "Poor"
        else:
            health = "Critical"

        # ── Risk tier — derived from the score against policy
        # thresholds, replacing the old manually-set static field.
        if total >= policy.risk_low_min_score:
            risk_tier = RiskTier.LOW
        elif total >= policy.risk_medium_min_score:
            risk_tier = RiskTier.MEDIUM
        else:
            risk_tier = RiskTier.HIGH

        if vendor.risk_tier != risk_tier:
            vendor.risk_tier = risk_tier
            await self.db.flush()

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "category": vendor.category.value if vendor.category else None,
            "policy_used": policy.name,
            "total_score": total,
            "health": health,
            "risk_tier": risk_tier.value,
            "breakdown": {
                "status_subscore": status_subscore,
                "document_subscore": doc_subscore,
                "expiry_subscore": expiry_subscore,
                "diversity_subscore": diversity_subscore,
                "weights_applied": {
                    "status": round(w_status, 3),
                    "documents": round(w_docs, 3),
                    "expiry": round(w_expiry, 3),
                    "diversity": round(w_div, 3),
                },
                "finding_penalty": finding_penalty,
                "required_document_types": required_types,
            },
            "grade": _score_to_grade(total),
        }

    # ─── Vendor health score (fleet rollup) ───────────────────

    async def get_fleet_health_score(self) -> dict:
        """
        Fleet-wide rollup of the per-vendor health score (Feature 17):
        average score across all active vendors, the equivalent overall
        grade, and a count of vendors per grade so the dashboard can show
        distribution, not just a single number.
        """
        result = await self.db.execute(
            select(Vendor).where(Vendor.is_active == True)
        )
        vendors = list(result.scalars().all())

        if not vendors:
            return {
                "avg_score": 0.0,
                "grade": "N/A",
                "vendor_count": 0,
                "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
            }

        scores = []
        grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for v in vendors:
            score_data = await self.compute_vendor_score(v.id)
            total_score = score_data.get("total_score", 0)
            grade = score_data.get("grade", "F")
            scores.append(total_score)
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        avg_score = round(sum(scores) / len(scores), 1)

        return {
            "avg_score": avg_score,
            "grade": _score_to_grade(int(avg_score)),
            "vendor_count": len(vendors),
            "grade_distribution": grade_distribution,
        }

    # ─── Analytics (Module 9) ──────────────────────────────────

    async def get_analytics(self, months: int = 6) -> dict:
        """
        Business-intelligence rollup for the Analytics page:
          - monthly_compliance_trend: compliance rate for each vendor
            "onboarding cohort" (grouped by the month a vendor was created)
            over the last `months` months. The platform doesn't keep a
            separate point-in-time compliance-history table, so this is an
            honest cohort view — the current compliance rate of vendors
            added in each month — rather than a fabricated historical replay.
          - regional_analysis: vendor count, compliance rate, and average
            score per region.
          - risk_distribution: risk-tier breakdown, both fleet-wide and
            per vendor category.
          - most_common_violations: the most frequent compliance findings
            (by rule_code) across all active vendors, with severity and
            how many distinct vendors triggered each one.
        """
        today = date.today()
        result = await self.db.execute(select(Vendor).where(Vendor.is_active == True))
        vendors = list(result.scalars().all())

        # ── Monthly compliance trend (by onboarding cohort) ─────
        buckets: dict[str, list[Vendor]] = {}
        month_keys = []
        cursor = today.replace(day=1)
        for _ in range(months):
            key = cursor.strftime("%Y-%m")
            month_keys.append(key)
            buckets[key] = []
            # step back one month
            prev_month_last_day = cursor - timedelta(days=1)
            cursor = prev_month_last_day.replace(day=1)
        month_keys.reverse()

        for v in vendors:
            created = getattr(v, "created_at", None)
            if not created:
                continue
            key = created.strftime("%Y-%m") if hasattr(created, "strftime") else str(created)[:7]
            if key in buckets:
                buckets[key].append(v)

        monthly_trend = []
        for key in month_keys:
            cohort = buckets[key]
            total = len(cohort)
            compliant = sum(1 for v in cohort if v.status == VendorStatus.COMPLIANT)
            rate = round((compliant / total) * 100, 1) if total else 0.0
            monthly_trend.append({
                "month": key,
                "vendors_onboarded": total,
                "compliant": compliant,
                "compliance_rate_pct": rate,
            })

        # ── Regional analysis ───────────────────────────────────
        region_map: dict[str, list[Vendor]] = {}
        for v in vendors:
            key = v.region or "Unassigned"
            region_map.setdefault(key, []).append(v)

        regional_analysis = []
        for region, vs in sorted(region_map.items(), key=lambda kv: -len(kv[1])):
            total = len(vs)
            compliant = sum(1 for v in vs if v.status == VendorStatus.COMPLIANT)
            non_compliant = sum(1 for v in vs if v.status == VendorStatus.NON_COMPLIANT)
            scores = [await self._vendor_score_only(v.id) for v in vs]
            avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
            regional_analysis.append({
                "region": region,
                "total_vendors": total,
                "compliant": compliant,
                "non_compliant": non_compliant,
                "compliance_rate_pct": round((compliant / total) * 100, 1) if total else 0.0,
                "avg_score": avg_score,
            })

        # ── Risk distribution (fleet-wide + per category) ───────
        risk_fleet = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        risk_by_category: dict[str, dict[str, int]] = {}
        for v in vendors:
            risk_fleet[v.risk_tier.value] = risk_fleet.get(v.risk_tier.value, 0) + 1
            cat = v.category.value if v.category else "OTHER"
            risk_by_category.setdefault(cat, {"LOW": 0, "MEDIUM": 0, "HIGH": 0})
            risk_by_category[cat][v.risk_tier.value] += 1

        # ── Most common violations (findings across active vendors) ─
        findings_result = await self.db.execute(
            select(Finding, Vendor.id)
            .join(Analysis, Finding.analysis_id == Analysis.id)
            .join(Document, Analysis.document_id == Document.id)
            .join(Vendor, Document.vendor_id == Vendor.id)
            .where(Vendor.is_active == True)
        )
        rows = findings_result.all()
        violation_map: dict[str, dict] = {}
        for finding, vendor_id in rows:
            entry = violation_map.setdefault(finding.rule_code, {
                "rule_code": finding.rule_code,
                "message": finding.message,
                "count": 0,
                "vendor_ids": set(),
                "severity": finding.severity.value,
            })
            entry["count"] += 1
            entry["vendor_ids"].add(vendor_id)
            # Keep the highest severity seen for this rule code
            severity_rank = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
            if severity_rank.get(finding.severity.value, 0) > severity_rank.get(entry["severity"], 0):
                entry["severity"] = finding.severity.value

        most_common_violations = sorted(
            (
                {
                    "rule_code": e["rule_code"],
                    "message": e["message"],
                    "occurrences": e["count"],
                    "vendors_affected": len(e["vendor_ids"]),
                    "severity": e["severity"],
                }
                for e in violation_map.values()
            ),
            key=lambda e: e["occurrences"],
            reverse=True,
        )[:10]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "monthly_compliance_trend": monthly_trend,
            "regional_analysis": regional_analysis,
            "risk_distribution": {
                "fleet_wide": risk_fleet,
                "by_category": risk_by_category,
            },
            "most_common_violations": most_common_violations,
        }

    # ─── Vendor timeline (Module 8) ────────────────────────────

    async def get_vendor_timeline(self, vendor_id: str) -> dict:
        """
        Chronological lifecycle timeline for a single vendor (Module 8 /
        Feature 18): Vendor Created -> Insurance Uploaded -> AI Analysis
        Completed -> Manual Review -> Approved -> Reminder Sent -> Renewed
        -> Audit Completed, built from real rows (documents, analyses,
        notification logs) rather than a separate hand-maintained event
        table, so it can't drift out of sync with what actually happened.
        """
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            return {"error": "Vendor not found"}

        events: list[dict] = []

        events.append({
            "type": "VENDOR_CREATED",
            "label": "Vendor Created",
            "timestamp": vendor.created_at.isoformat(),
            "detail": f"{vendor.name} added" + (
                f" by {vendor.created_by.full_name}" if getattr(vendor, "created_by", None) else ""
            ),
        })

        docs_result = await self.db.execute(
            select(Document)
            .where(Document.vendor_id == vendor_id)
            .order_by(Document.created_at)
        )
        docs = list(docs_result.scalars().all())

        for doc in docs:
            events.append({
                "type": "DOCUMENT_UPLOADED",
                "label": "Insurance Uploaded" if doc.document_type == DocumentType.COI else "Document Uploaded",
                "timestamp": doc.created_at.isoformat(),
                "detail": f"{doc.filename} ({doc.document_type.value})",
            })

            analyses_result = await self.db.execute(
                select(Analysis)
                .where(Analysis.document_id == doc.id)
                .order_by(Analysis.created_at)
            )
            analyses = list(analyses_result.scalars().all())
            for analysis in analyses:
                events.append({
                    "type": "AI_ANALYSIS_COMPLETED",
                    "label": "AI Analysis Completed",
                    "timestamp": analysis.created_at.isoformat(),
                    "detail": f"{doc.filename} — confidence {round(analysis.confidence_score * 100)}%",
                })
                if analysis.status == AnalysisStatus.NEEDS_REVIEW:
                    events.append({
                        "type": "MANUAL_REVIEW",
                        "label": "Manual Review Requested",
                        "timestamp": analysis.updated_at.isoformat(),
                        "detail": f"{doc.filename} flagged for analyst review",
                    })
                elif analysis.status == AnalysisStatus.COMPLIANT:
                    events.append({
                        "type": "APPROVED",
                        "label": "Approved",
                        "timestamp": analysis.updated_at.isoformat(),
                        "detail": f"{doc.filename} passed compliance checks",
                    })
                elif analysis.status == AnalysisStatus.NON_COMPLIANT:
                    events.append({
                        "type": "REJECTED",
                        "label": "Document Rejected",
                        "timestamp": analysis.updated_at.isoformat(),
                        "detail": f"{doc.filename} failed compliance checks",
                    })

        notif_result = await self.db.execute(
            select(VendorNotificationLog)
            .where(VendorNotificationLog.vendor_id == vendor_id)
            .order_by(VendorNotificationLog.created_at)
        )
        for log in notif_result.scalars().all():
            events.append({
                "type": "REMINDER_SENT",
                "label": "Reminder Sent",
                "timestamp": log.created_at.isoformat(),
                "detail": f"{log.alert_type} — {log.urgency_bucket}" + ("" if log.success else " (failed)"),
            })

        if vendor.updated_at and vendor.updated_at > vendor.created_at:
            events.append({
                "type": "VENDOR_UPDATED",
                "label": "Vendor Renewed / Updated",
                "timestamp": vendor.updated_at.isoformat(),
                "detail": f"Status: {vendor.status.value}, Risk: {vendor.risk_tier.value}",
            })

        events.sort(key=lambda e: e["timestamp"])

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "events": events,
        }

    async def _vendor_score_only(self, vendor_id: str) -> float:
        """Lightweight helper for analytics aggregation — reuses the full
        scoring logic but returns just the numeric total."""
        data = await self.compute_vendor_score(vendor_id)
        return data.get("total_score", 0)

    # ─── Reports ─────────────────────────────────────────────

    async def get_compliance_report(self, filters: dict | None = None) -> dict:
        """Full compliance report for active vendors, optionally narrowed by
        filters: status, risk_tier, category, business_unit, region, search."""
        filters = filters or {}
        query = select(Vendor).where(Vendor.is_active == True)
        if filters.get("status"):
            query = query.where(Vendor.status == filters["status"])
        if filters.get("risk_tier"):
            query = query.where(Vendor.risk_tier == filters["risk_tier"])
        if filters.get("category"):
            query = query.where(Vendor.category == filters["category"])
        if filters.get("vendor_type"):
            query = query.where(Vendor.vendor_type == filters["vendor_type"])
        if filters.get("business_unit"):
            query = query.where(Vendor.business_unit.ilike(f"%{filters['business_unit']}%"))
        if filters.get("region"):
            query = query.where(Vendor.region.ilike(f"%{filters['region']}%"))
        if filters.get("insurance_provider"):
            query = query.where(Vendor.insurance_provider.ilike(f"%{filters['insurance_provider']}%"))
        if filters.get("assigned_analyst"):
            # Name-based search (Report page filters by analyst name, not
            # the raw user id) — join onto User so partial names match.
            term = f"%{filters['assigned_analyst']}%"
            query = query.join(User, Vendor.assigned_analyst_id == User.id).where(
                User.full_name.ilike(term)
            )
        if filters.get("document_type"):
            # Vendor has at least one document of this type.
            query = (
                query.join(Document, Document.vendor_id == Vendor.id)
                .where(Document.document_type == filters["document_type"])
                .distinct()
            )
        if filters.get("expiry_before"):
            # Either coverage type expiring on/before the given date —
            # matches the "Expiry Date" advanced-filter requirement.
            cutoff = filters["expiry_before"]
            query = query.where(
                or_(
                    and_(Vendor.gl_expiry.isnot(None), Vendor.gl_expiry <= cutoff),
                    and_(Vendor.wc_expiry.isnot(None), Vendor.wc_expiry <= cutoff),
                )
            )
        if filters.get("search"):
            term = f"%{filters['search']}%"
            query = query.where(Vendor.name.ilike(term))

        result = await self.db.execute(query)
        vendors = list(result.scalars().unique().all())

        report_rows = []
        for v in vendors:
            score_data = await self.compute_vendor_score(v.id)
            doc_count = await self._count(Document, Document.vendor_id == v.id)
            report_rows.append({
                "id": v.id,
                "name": v.name,
                "email": v.email,
                # Classification (for filtering/grouping)
                "category": v.category.value if v.category else None,
                "vendor_type": v.vendor_type.value if v.vendor_type else None,
                "business_unit": v.business_unit,
                "region": v.region,
                "insurance_provider": v.insurance_provider,
                "assigned_analyst": v.assigned_analyst.full_name if getattr(v, "assigned_analyst", None) else None,
                # Compliance Information
                "status": v.status.value,
                "risk_tier": v.risk_tier.value,
                # Score Information
                "total_score": score_data.get("total_score", 0),
                "grade": score_data.get("grade", "F"),
                "health": score_data.get("health", "Unknown"),
                # Documents
                "document_count": doc_count,
                # Expiry Information
                "gl_expiry": v.gl_expiry,
                "wc_expiry": v.wc_expiry,
                # Diversity
                "diversity_types": v.diversity_types or [],
                # Business Priority
                "priority": (
                    "HIGH"
                    if v.status == VendorStatus.NON_COMPLIANT
                    else "MEDIUM"
                    if v.status == VendorStatus.NEEDS_REVIEW
                    else "LOW"
                ),
                # Expiry Flag — checks both gl_expiry AND wc_expiry
                "expiry_flag": (
                    "EXPIRED"
                    if _any_expired(v.gl_expiry, v.wc_expiry, today=date.today())
                    else "ACTIVE"
                ),
            })

        risk_order = {
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }

        status_order = {
            "NON_COMPLIANT": 3,
            "NEEDS_REVIEW": 2,
            "COMPLIANT": 1,
        }

        report_rows.sort(
            key=lambda r: (
                risk_order.get(r["risk_tier"], 0),
                status_order.get(r["status"], 0),
                -r["total_score"],
            ),
            reverse=True,
        )

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

    async def _get_expiring_vendors(self, days: int, include_overdue: bool = False) -> list[Vendor]:
        today = date.today()
        cutoff = (today + timedelta(days=days)).isoformat()
        today_str = today.isoformat()
        # When include_overdue is set, don't filter out coverage that has
        # already lapsed (no lower bound on the expiry date) — used by the
        # alerts feed so overdue GL/WC certificates keep showing up instead
        # of disappearing the day after they expire.
        lower_bound_gl = [] if include_overdue else [Vendor.gl_expiry >= today_str]
        lower_bound_wc = [] if include_overdue else [Vendor.wc_expiry >= today_str]
        result = await self.db.execute(
            select(Vendor).where(
                and_(
                    Vendor.is_active == True,
                    Vendor.gl_expiry.isnot(None),
                    *lower_bound_gl,
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
                    *lower_bound_wc,
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


def _expiry_priority(days_left: int) -> tuple[str, bool]:
    """Map days-until-expiry to a (priority, escalated) pair.
    Overdue or within the escalation window (DAYS_ESCALATION) -> CRITICAL +
    escalated=True. Within the critical window -> CRITICAL. Otherwise HIGH."""
    if days_left <= DAYS_ESCALATION:
        return "CRITICAL", True
    if days_left <= DAYS_EXPIRY_CRITICAL:
        return "CRITICAL", False
    return "HIGH", False


def _any_expired(*date_strings: str | None, today: date) -> bool:
    """Return True if *any* of the given date strings is non‑None,
    parseable as ISO‑8601, and earlier than *today*.  Invalid strings
    are silently treated as not‐expired (safe default)."""
    for ds in date_strings:
        if not ds:
            continue
        try:
            if date.fromisoformat(ds) < today:
                return True
        except (ValueError, TypeError):
            pass
    return False


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