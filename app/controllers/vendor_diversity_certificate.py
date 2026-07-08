from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db

from app.schemas.vendor_diversity_certificate import (
    VendorDiversityCertificateCreate,
    VendorDiversityCertificateUpdate,
    VendorDiversityCertificateResponse,
)

from app.services.vendor_diversity_certificate import (
    VendorDiversityCertificateService,
)

router = APIRouter(
    prefix="/vendor-diversity-certificates",
    tags=["Vendor Diversity Certificates"]
)


@router.post("/", response_model=VendorDiversityCertificateResponse)
def create_certificate(
    certificate: VendorDiversityCertificateCreate,
    db: Session = Depends(get_db)
):
    return VendorDiversityCertificateService.create_certificate(
        db,
        certificate
    )


@router.get("/", response_model=List[VendorDiversityCertificateResponse])
def get_all_certificates(
    db: Session = Depends(get_db)
):
    return VendorDiversityCertificateService.get_all_certificates(db)


@router.get("/{certificate_id}", response_model=VendorDiversityCertificateResponse)
def get_certificate(
    certificate_id: int,
    db: Session = Depends(get_db)
):
    return VendorDiversityCertificateService.get_certificate_by_id(
        db,
        certificate_id
    )


@router.put("/{certificate_id}", response_model=VendorDiversityCertificateResponse)
def update_certificate(
    certificate_id: int,
    certificate: VendorDiversityCertificateUpdate,
    db: Session = Depends(get_db)
):
    return VendorDiversityCertificateService.update_certificate(
        db,
        certificate_id,
        certificate
    )


@router.delete("/{certificate_id}")
def delete_certificate(
    certificate_id: int,
    db: Session = Depends(get_db)
):
    return VendorDiversityCertificateService.delete_certificate(
        db,
        certificate_id
    )
