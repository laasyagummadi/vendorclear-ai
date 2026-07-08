from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.vendor_policy import VendorPolicy
from app.models.vendor_diversity_certificate import (
    VendorDiversityCertificate,
)
from app.models.alert import Alert

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/")
def dashboard(
    db: Session = Depends(get_db)
):
    today = date.today()

    total_vendor_policies = db.query(VendorPolicy).count()

    total_diversity_certificates = (
        db.query(VendorDiversityCertificate).count()
    )

    expired_vendor_policies = (
        db.query(VendorPolicy)
        .filter(VendorPolicy.expiry_date < today)
        .count()
    )

    expired_diversity_certificates = (
        db.query(VendorDiversityCertificate)
        .filter(
            VendorDiversityCertificate.expiry_date < today
        )
        .count()
    )

    total_alerts = db.query(Alert).count()

    return {
        "total_vendor_policies": total_vendor_policies,
        "total_diversity_certificates": total_diversity_certificates,
        "expired_vendor_policies": expired_vendor_policies,
        "expired_diversity_certificates": expired_diversity_certificates,
        "total_alerts": total_alerts
    }
