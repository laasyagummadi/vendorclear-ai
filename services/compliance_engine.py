from datetime import date

from app.models.vendor_policy import VendorPolicy
from app.models.vendor_diversity_certificate import (
    VendorDiversityCertificate,
)


class ComplianceEngine:

    @staticmethod
    def evaluate(
        policy: VendorPolicy,
        certificate: VendorDiversityCertificate
    ):
        alerts = []
        risk_score = 0

        today = date.today()

        # -----------------------------------
        # Vendor Policy Checks
        # -----------------------------------

        # Check Policy Expiry
        if policy.expiry_date and policy.expiry_date < today:
            alerts.append({
                "message": "Vendor policy has expired.",
                "severity": "High"
            })
            risk_score += 40

        # Check Policy Status
        if (
            policy.compliance_status
            and policy.compliance_status.lower() != "active"
        ):
            alerts.append({
                "message": "Vendor policy is inactive.",
                "severity": "Medium"
            })
            risk_score += 20

        # -----------------------------------
        # Vendor Diversity Certificate Checks
        # -----------------------------------

        # Check Certificate Expiry
        if certificate.expiry_date and certificate.expiry_date < today:
            alerts.append({
                "message": "Vendor diversity certificate has expired.",
                "severity": "High"
            })
            risk_score += 40

        # Check Certificate Status
        if (
            certificate.status
            and certificate.status.lower() != "active"
        ):
            alerts.append({
                "message": "Vendor diversity certificate is inactive.",
                "severity": "Medium"
            })
            risk_score += 20

        # -----------------------------------
        # Final Compliance Status
        # -----------------------------------

        if risk_score == 0:
            compliance_status = "Compliant"
        elif risk_score <= 40:
            compliance_status = "Low Risk"
        elif risk_score <= 70:
            compliance_status = "Medium Risk"
        else:
            compliance_status = "High Risk"

        return {
            "vendor_name": policy.vendor_name,
            "compliance_status": compliance_status,
            "risk_score": risk_score,
            "alerts": alerts
        }
