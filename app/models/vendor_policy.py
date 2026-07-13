from sqlalchemy import Column, Integer, String, Date

from app.models.base import Base


class VendorPolicy(Base):
    __tablename__ = "vendor_policies"

    id = Column(Integer, primary_key=True, index=True)

    vendor_name = Column(String(255), nullable=False)

    policy_name = Column(String(255), nullable=False)

    compliance_status = Column(String(50), nullable=False)

    expiry_date = Column(Date, nullable=False)
