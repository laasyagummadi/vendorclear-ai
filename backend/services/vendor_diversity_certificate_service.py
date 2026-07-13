# ─────────────────────────────────────────────────────────────
#  services/vendor_diversity_certificate_service.py  (Nirupama)
#  Standalone service for diversity certificate validation
#  and vendor diversity programme management.
# ─────────────────────────────────────────────────────────────
"""
VendorDiversityCertificateService

Responsibilities:
  - Validate diversity certificate data extracted by Gemini AI
  - Determine certification eligibility thresholds
  - Generate diversity programme insights
  - Produce diversity audit reports
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


# ── Enums & constants ─────────────────────────────────────────

class CertificationType(str, Enum):
    MBE = "MBE"          # Minority Business Enterprise
    WBE = "WBE"          # Women Business Enterprise
    DBE = "DBE"          # Disadvantaged Business Enterprise
    SBE = "SBE"          # Small Business Enterprise
    SDVOSB = "SDVOSB"   # Service-Disabled Veteran-Owned
    VOSB = "VOSB"        # Veteran-Owned Small Business
    HUBZONE = "HUBZone"  # HUBZone Small Business
    UNKNOWN = "UNKNOWN"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    EXPIRING_SOON = "EXPIRING_SOON"
    INVALID_OWNERSHIP = "INVALID_OWNERSHIP"
    MISSING_FIELDS = "MISSING_FIELDS"
    UNKNOWN = "UNKNOWN"


MINIMUM_OWNERSHIP_PCT = 51.0    # Federal / most state minimum
EXPIRY_WARNING_DAYS = 60        # Flag as expiring soon


# ── Data classes ──────────────────────────────────────────────

@dataclass
class DiversityCertificate:
    cert_type: CertificationType
    cert_body: Optional[str]
    cert_number: Optional[str]
    ownership_pct: Optional[float]
    expiry_date: Optional[str]           # ISO YYYY-MM-DD
    issuer_state: Optional[str] = None
    is_federal: bool = False
    notes: str = ""


@dataclass
class ValidationResult:
    status: ValidationStatus
    is_valid: bool
    messages: list[str] = field(default_factory=list)
    days_until_expiry: Optional[int] = None
    ownership_gap: Optional[float] = None   # how far below 51 %


@dataclass
class DiversityProgrammeInsight:
    vendor_id: str
    vendor_name: str
    certifications: list[DiversityCertificate]
    validation_results: list[ValidationResult]
    overall_status: ValidationStatus
    eligible_spend_categories: list[str]
    recommendations: list[str]


# ── Service class ─────────────────────────────────────────────

class VendorDiversityCertificateService:
    """
    Validate, score, and generate insights for vendor diversity certificates.
    Used downstream by DocumentController and ComplianceService.
    """

    # ─── Validation ───────────────────────────────────────────

    def validate_certificate(self, cert: DiversityCertificate) -> ValidationResult:
        """Apply all validation rules to a single certificate."""
        messages: list[str] = []
        days_left: Optional[int] = None
        ownership_gap: Optional[float] = None

        # 1. Check required fields
        missing = []
        if not cert.cert_type or cert.cert_type == CertificationType.UNKNOWN:
            missing.append("cert_type")
        if not cert.cert_number:
            missing.append("cert_number")
        if cert.ownership_pct is None:
            missing.append("ownership_pct")
        if not cert.expiry_date:
            missing.append("expiry_date")

        if missing:
            return ValidationResult(
                status=ValidationStatus.MISSING_FIELDS,
                is_valid=False,
                messages=[f"Missing required field(s): {', '.join(missing)}"],
            )

        # 2. Check ownership percentage
        if cert.ownership_pct < MINIMUM_OWNERSHIP_PCT:
            ownership_gap = MINIMUM_OWNERSHIP_PCT - cert.ownership_pct
            messages.append(
                f"Ownership {cert.ownership_pct}% is below the required {MINIMUM_OWNERSHIP_PCT}%. "
                f"Gap: {ownership_gap:.1f}%."
            )
            return ValidationResult(
                status=ValidationStatus.INVALID_OWNERSHIP,
                is_valid=False,
                messages=messages,
                ownership_gap=ownership_gap,
            )

        # 3. Check expiry date
        try:
            exp = date.fromisoformat(cert.expiry_date)
            today = date.today()
            days_left = (exp - today).days

            if days_left < 0:
                messages.append(f"Certificate expired {abs(days_left)} day(s) ago ({cert.expiry_date}).")
                return ValidationResult(
                    status=ValidationStatus.EXPIRED,
                    is_valid=False,
                    messages=messages,
                    days_until_expiry=days_left,
                )

            if days_left <= EXPIRY_WARNING_DAYS:
                messages.append(
                    f"Certificate expires in {days_left} day(s) ({cert.expiry_date}). Renewal recommended."
                )
                return ValidationResult(
                    status=ValidationStatus.EXPIRING_SOON,
                    is_valid=True,   # still valid but flagged
                    messages=messages,
                    days_until_expiry=days_left,
                )

        except ValueError:
            messages.append(f"Expiry date '{cert.expiry_date}' is not a valid ISO date.")
            return ValidationResult(
                status=ValidationStatus.MISSING_FIELDS,
                is_valid=False,
                messages=messages,
            )

        # All checks passed
        messages.append(
            f"{cert.cert_type.value} certificate #{cert.cert_number} is valid "
            f"(expires {cert.expiry_date}, {days_left} days remaining)."
        )
        return ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            messages=messages,
            days_until_expiry=days_left,
        )

    def validate_all(
        self, certs: list[DiversityCertificate]
    ) -> tuple[list[ValidationResult], ValidationStatus]:
        """Validate a list of certificates; return (results, worst_status)."""
        results = [self.validate_certificate(c) for c in certs]
        # Worst status ordering
        rank = {
            ValidationStatus.VALID: 0,
            ValidationStatus.EXPIRING_SOON: 1,
            ValidationStatus.UNKNOWN: 2,
            ValidationStatus.MISSING_FIELDS: 3,
            ValidationStatus.INVALID_OWNERSHIP: 4,
            ValidationStatus.EXPIRED: 5,
        }
        worst = max(results, key=lambda r: rank.get(r.status, 2), default=None)
        overall = worst.status if worst else ValidationStatus.UNKNOWN
        return results, overall

    # ─── Insights & recommendations ───────────────────────────

    def generate_insight(
        self,
        vendor_id: str,
        vendor_name: str,
        certs: list[DiversityCertificate],
    ) -> DiversityProgrammeInsight:
        results, overall = self.validate_all(certs)

        spend_categories = self._eligible_spend_categories(certs)
        recommendations = self._build_recommendations(certs, results)

        return DiversityProgrammeInsight(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            certifications=certs,
            validation_results=results,
            overall_status=overall,
            eligible_spend_categories=spend_categories,
            recommendations=recommendations,
        )

    def _eligible_spend_categories(self, certs: list[DiversityCertificate]) -> list[str]:
        mapping = {
            CertificationType.MBE: ["Minority Business Set-Aside", "MWBE Spend"],
            CertificationType.WBE: ["Women Business Set-Aside", "MWBE Spend"],
            CertificationType.DBE: ["DBE Federal Contract Spend", "DOT Subcontracting"],
            CertificationType.SBE: ["Small Business Set-Aside"],
            CertificationType.SDVOSB: ["VA SDVOSB Set-Aside", "Federal SDVOSB"],
            CertificationType.VOSB: ["VA VOSB Set-Aside"],
            CertificationType.HUBZONE: ["HUBZone Federal Set-Aside"],
        }
        categories: list[str] = []
        for c in certs:
            categories.extend(mapping.get(c.cert_type, []))
        return list(dict.fromkeys(categories))  # deduplicate preserving order

    def _build_recommendations(
        self,
        certs: list[DiversityCertificate],
        results: list[ValidationResult],
    ) -> list[str]:
        recs: list[str] = []
        for cert, result in zip(certs, results):
            if result.status == ValidationStatus.EXPIRED:
                recs.append(
                    f"Renew {cert.cert_type.value} certificate #{cert.cert_number} immediately."
                )
            elif result.status == ValidationStatus.EXPIRING_SOON:
                recs.append(
                    f"Initiate renewal of {cert.cert_type.value} certificate #{cert.cert_number} "
                    f"({result.days_until_expiry} days remaining)."
                )
            elif result.status == ValidationStatus.INVALID_OWNERSHIP:
                recs.append(
                    f"{cert.cert_type.value} requires ≥{MINIMUM_OWNERSHIP_PCT}% diverse ownership. "
                    f"Current: {cert.ownership_pct}%."
                )
            elif result.status == ValidationStatus.MISSING_FIELDS:
                recs.append(
                    f"Complete missing fields for {cert.cert_type.value} certificate to pass validation."
                )
        if not recs:
            recs.append("All diversity certificates are current. Schedule renewals before expiry.")
        return recs

    # ─── Serialization ────────────────────────────────────────

    @staticmethod
    def from_analysis_data(extracted: dict) -> DiversityCertificate:
        """Build a DiversityCertificate from Gemini-extracted data dict."""
        cert_type_str = (extracted.get("cert_type") or "UNKNOWN").upper()
        try:
            cert_type = CertificationType(cert_type_str)
        except ValueError:
            cert_type = CertificationType.UNKNOWN

        return DiversityCertificate(
            cert_type=cert_type,
            cert_body=extracted.get("cert_body"),
            cert_number=extracted.get("cert_number"),
            ownership_pct=extracted.get("ownership_pct"),
            expiry_date=extracted.get("expiry_date"),
        )

    @staticmethod
    def insight_to_dict(insight: DiversityProgrammeInsight) -> dict:
        return {
            "vendor_id": insight.vendor_id,
            "vendor_name": insight.vendor_name,
            "overall_status": insight.overall_status.value,
            "eligible_spend_categories": insight.eligible_spend_categories,
            "recommendations": insight.recommendations,
            "certifications": [
                {
                    "cert_type": c.cert_type.value,
                    "cert_body": c.cert_body,
                    "cert_number": c.cert_number,
                    "ownership_pct": c.ownership_pct,
                    "expiry_date": c.expiry_date,
                }
                for c in insight.certifications
            ],
            "validation_results": [
                {
                    "status": r.status.value,
                    "is_valid": r.is_valid,
                    "messages": r.messages,
                    "days_until_expiry": r.days_until_expiry,
                }
                for r in insight.validation_results
            ],
        }
