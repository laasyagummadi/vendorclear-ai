from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.analysis import AnalysisStatus
from app.models.finding import FindingSeverity


class FindingOut(BaseModel):
    id: str
    analysis_id: str
    severity: FindingSeverity
    rule_code: str
    message: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisOut(BaseModel):
    id: str
    document_id: str
    raw_text: Optional[str] = None
    extracted_fields: Optional[dict] = None
    confidence_score: float
    status: AnalysisStatus

    # COI fields
    insured_name: Optional[str] = None
    insurer_name: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_type: Optional[str] = None
    general_liability_limit_usd: Optional[float] = None
    workers_comp_limit_usd: Optional[float] = None
    auto_liability_limit_usd: Optional[float] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    additional_insured: Optional[bool] = None
    certificate_holder: Optional[str] = None

    # Diversity cert fields
    cert_body: Optional[str] = None
    cert_type: Optional[str] = None
    cert_number: Optional[str] = None
    ownership_pct: Optional[float] = None

    created_at: datetime
    updated_at: datetime
    findings: List[FindingOut] = []

    model_config = ConfigDict(from_attributes=True)
