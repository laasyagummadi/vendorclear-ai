from sqlalchemy.orm import Session

from app.models.vendor_diversity_certificate import VendorDiversityCertificate
from app.schemas.vendor_diversity_certificate import (
    VendorDiversityCertificateCreate,
    VendorDiversityCertificateUpdate,
)


class VendorDiversityCertificateRepository:

    @staticmethod
    def create(db: Session, cert: VendorDiversityCertificateCreate):
        db_cert = VendorDiversityCertificate(**cert.model_dump())
        db.add(db_cert)
        db.commit()
        db.refresh(db_cert)
        return db_cert

    @staticmethod
    def get_all(db: Session):
        return db.query(VendorDiversityCertificate).all()

    @staticmethod
    def get_by_id(db: Session, cert_id: int):
        return db.query(VendorDiversityCertificate).filter(
            VendorDiversityCertificate.id == cert_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        db_cert: VendorDiversityCertificate,
        cert: VendorDiversityCertificateUpdate,
    ):
        update_data = cert.model_dump()
        for key, value in update_data.items():
            setattr(db_cert, key, value)
        db.commit()
        db.refresh(db_cert)
        return db_cert

    @staticmethod
    def delete(db: Session, db_cert: VendorDiversityCertificate):
        db.delete(db_cert)
        db.commit()
