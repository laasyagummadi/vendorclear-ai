from datetime import date
from pydantic import BaseModel


class VendorDiversityCertificateCreate(BaseModel):
    vendor_name: str
    certificate_number: str
    issue_date: date
    expiry_date: date
    status: str


class VendorDiversityCertificateUpdate(BaseModel):
    vendor_name: str
    certificate_number: str
    issue_date: date
    expiry_date: date
    status: str


class VendorDiversityCertificateResponse(BaseModel):
    id: int
    vendor_name: str
    certificate_number: str
    issue_date: date
    expiry_date: date
    status: str

    class Config:
        from_attributes = True
