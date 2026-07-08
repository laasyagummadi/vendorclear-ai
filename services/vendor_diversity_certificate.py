from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repository.vendor_diversity_certificate import (
    VendorDiversityCertificateRepository,
)
from app.schemas.vendor_diversity_certificate import (
    VendorDiversityCertificateCreate,
    VendorDiversityCertificateUpdate,
)


class VendorDiversityCertificateService:

    @staticmethod
    def create_certificate(
        db: Session,
        certificate: VendorDiversityCertificateCreate,
    ):
        return VendorDiversityCertificateRepository.create(
            db,
            certificate,
        )

    @staticmethod
    def get_all_certificates(db: Session):
        return VendorDiversityCertificateRepository.get_all(db)

    @staticmethod
    def get_certificate_by_id(
        db: Session,
        certificate_id: int,
    ):
        certificate = VendorDiversityCertificateRepository.get_by_id(
            db,
            certificate_id,
        )

        if not certificate:
            raise HTTPException(
                status_code=404,
                detail="Certificate not found",
            )

        return certificate

    @staticmethod
    def update_certificate(
        db: Session,
        certificate_id: int,
        certificate: VendorDiversityCertificateUpdate,
    ):
        db_certificate = (
            VendorDiversityCertificateRepository.get_by_id(
                db,
                certificate_id,
            )
        )

        if not db_certificate:
            raise HTTPException(
                status_code=404,
                detail="Certificate not found",
            )

        return VendorDiversityCertificateRepository.update(
            db,
            db_certificate,
            certificate,
        )

    @staticmethod
    def delete_certificate(
        db: Session,
        certificate_id: int,
    ):
        db_certificate = (
            VendorDiversityCertificateRepository.get_by_id(
                db,
                certificate_id,
            )
        )

        if not db_certificate:
            raise HTTPException(
                status_code=404,
                detail="Certificate not found",
            )

        VendorDiversityCertificateRepository.delete(
            db,
            db_certificate,
        )

        return {"message": "Certificate deleted successfully"}
