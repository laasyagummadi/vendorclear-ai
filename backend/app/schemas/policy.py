# ─────────────────────────────────────────────────────────────
#  app/schemas/policy.py  —  CompliancePolicy request/response schemas
# ─────────────────────────────────────────────────────────────
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, model_validator

from app.models.vendor import VendorCategory


class CompliancePolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    weight_status: float = 0.40
    weight_documents: float = 0.30
    weight_expiry: float = 0.20
    weight_diversity: float = 0.10
    finding_penalty_critical: float = 10.0
    finding_penalty_high: float = 5.0
    finding_penalty_medium: float = 2.0
    required_document_types: Optional[List[str]] = None
    risk_low_min_score: float = 75.0
    risk_medium_min_score: float = 50.0
    is_active: bool = True

    @model_validator(mode="after")
    def _check_weights(self):
        total = self.weight_status + self.weight_documents + self.weight_expiry + self.weight_diversity
        if total <= 0:
            raise ValueError("Policy weights must sum to a positive number")
        if self.risk_medium_min_score > self.risk_low_min_score:
            raise ValueError("risk_medium_min_score cannot exceed risk_low_min_score")
        return self


class CompliancePolicyCreate(CompliancePolicyBase):
    category: VendorCategory


class CompliancePolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight_status: Optional[float] = None
    weight_documents: Optional[float] = None
    weight_expiry: Optional[float] = None
    weight_diversity: Optional[float] = None
    finding_penalty_critical: Optional[float] = None
    finding_penalty_high: Optional[float] = None
    finding_penalty_medium: Optional[float] = None
    required_document_types: Optional[List[str]] = None
    risk_low_min_score: Optional[float] = None
    risk_medium_min_score: Optional[float] = None
    is_active: Optional[bool] = None


class CompliancePolicyResponse(CompliancePolicyBase):
    id: str
    category: VendorCategory
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
