# ─────────────────────────────────────────────────────────────
#  app/schemas/approvals.py  —  Approval workflow schemas
# ─────────────────────────────────────────────────────────────
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ApprovalPolicyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    version: int = Field(default=1, ge=1, le=2)
    requirements: dict[str, Any] = Field(default_factory=dict)


class ApprovalPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[int] = None
    requirements: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ApprovalPolicyOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: int
    requirements: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalSubmissionCreate(BaseModel):
    policy_id: str
    vendor_id: str
    document_ids: Optional[list[str]] = None


class ApprovalSubmissionDecision(BaseModel):
    notes: Optional[str] = None


class ApprovalSubmissionOut(BaseModel):
    id: str
    policy_id: str
    vendor_id: str
    status: str
    document_ids: Optional[list] = None
    requirement_results: Optional[dict] = None
    meets_requirements: Optional[bool] = None
    submitted_by_id: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
