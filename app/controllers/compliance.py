from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models.vendor_policy import VendorPolicy
from app.models.vendor_diversity_certificate import VendorDiversityCertificate

from app.services.compliance_engine import ComplianceEngine
from app.services.alert_service import AlertService

router = APIRouter(
    prefix="/compliance",
    tags=["Compliance"]
)


@router.get("/evaluate/{vendor_name}")
def evaluate_compliance(
    vendor_name: str,
    db: Session = Depends(get_sync_db)
):

    policy = (
        db.query(VendorPolicy)
        .filter(VendorPolicy.vendor_name == vendor_name)
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Vendor Policy not found"
        )

    certificate = (
        db.query(VendorDiversityCertificate)
        .filter(
            VendorDiversityCertificate.vendor_name == vendor_name
        )
        .first()
    )

    if not certificate:
        raise HTTPException(
            status_code=404,
            detail="Vendor Diversity Certificate not found"
        )

    result = ComplianceEngine.evaluate(
        policy,
        certificate
    )

    # Save alerts into database
    for alert in result["alerts"]:
        AlertService.create_alert(
            db=db,
            message=alert["message"],
            severity=alert["severity"]
        )

    return result
