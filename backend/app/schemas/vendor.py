# ─────────────────────────────────────────────────────────────
#  app/schemas/vendor.py  —  Vendor request/response schemas
# ─────────────────────────────────────────────────────────────
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator

from app.models.vendor import VendorStatus, RiskTier


# ── Create ────────────────────────────────────────────────────
class VendorCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    diversity_types: Optional[List[str]] = None
    gl_expiry: Optional[str] = None   # YYYY-MM-DD
    wc_expiry: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Vendor name cannot be empty")
        return v

    @field_validator("gl_expiry", "wc_expiry", mode="before")
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


# ── Update (all fields optional) ─────────────────────────────
class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    status: Optional[VendorStatus] = None
    risk_tier: Optional[RiskTier] = None
    compliance_score: Optional[float] = None
    diversity_types: Optional[List[str]] = None
    gl_expiry: Optional[str] = None
    wc_expiry: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ── Response ──────────────────────────────────────────────────
class VendorResponse(BaseModel):
    id: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    status: VendorStatus
    risk_tier: RiskTier
    compliance_score: Optional[float] = None
    diversity_types: Optional[List[str]] = None
    gl_expiry: Optional[str] = None
    wc_expiry: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str] = None

    model_config = {"from_attributes": True}


# ── List / filter query params ────────────────────────────────
class VendorFilterParams(BaseModel):
    status: Optional[VendorStatus] = None
    risk_tier: Optional[RiskTier] = None
    search: Optional[str] = None        # searches name, email, contact_name
    is_active: Optional[bool] = True
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ── Summary (for dashboard / list views) ─────────────────────
class VendorSummary(BaseModel):
    id: str
    name: str
    status: VendorStatus
    risk_tier: RiskTier
    compliance_score: Optional[float] = None
    gl_expiry: Optional[str] = None
    wc_expiry: Optional[str] = None

    model_config = {"from_attributes": True}
