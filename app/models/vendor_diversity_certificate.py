from sqlalchemy import Column, Integer, String, Date

from app.models.base import Base


class VendorDiversityCertificate(Base):
    __tablename__ = "vendor_diversity_certificates"

    id = Column(Integer, primary_key=True, index=True)

    vendor_name = Column(String(255), nullable=False)

    certificate_number = Column(String(100), nullable=False)

    issue_date = Column(Date)

    expiry_date = Column(Date)

    status = Column(String(50))
