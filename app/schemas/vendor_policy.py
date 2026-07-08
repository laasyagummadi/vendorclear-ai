from pydantic import BaseModel
from datetime import date


class VendorPolicyCreate(BaseModel):
    vendor_name: str
    policy_name: str
    compliance_status: str
    expiry_date: date


class VendorPolicyUpdate(BaseModel):
    vendor_name: str
    policy_name: str
    compliance_status: str
    expiry_date: date


class VendorPolicyResponse(BaseModel):
    id: int
    vendor_name: str
    policy_name: str
    compliance_status: str
    expiry_date: date

    class Config:
        from_attributes = True
