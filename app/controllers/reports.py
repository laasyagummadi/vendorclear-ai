from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models.vendor_policy import VendorPolicy
from app.models.vendor_diversity_certificate import VendorDiversityCertificate
from app.models.alert import Alert

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get("/compliance")
def compliance_report(
    db: Session = Depends(get_sync_db)
):
    policies = db.query(VendorPolicy).all()

    return {
        "total_policies": len(policies),
        "policies": policies
    }


@router.get("/alerts")
def alerts_report(
    db: Session = Depends(get_sync_db)
):
    alerts = db.query(Alert).all()

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }


@router.get("/diversity-certificates")
def diversity_report(
    db: Session = Depends(get_sync_db)
):
    certificates = db.query(
        VendorDiversityCertificate
    ).all()

    return {
        "total_certificates": len(certificates),
        "certificates": certificates
    }
