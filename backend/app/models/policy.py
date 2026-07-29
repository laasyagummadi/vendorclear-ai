# ─────────────────────────────────────────────────────────────
#  app/models/policy.py  —  CompliancePolicy ORM model
# ─────────────────────────────────────────────────────────────
"""
An admin-configurable scoring policy, one per vendor category
(Construction / Software / Electrical / Other). Replaces the old
hardcoded WEIGHT_STATUS / WEIGHT_DOCUMENTS / WEIGHT_EXPIRY /
WEIGHT_DIVERSITY constants that used to be applied identically to
every vendor regardless of category.

Each policy's four weights should sum to 1.0 (the service normalizes
them defensively either way, so a bad admin edit can't break scoring).
"""
from typing import Optional

from sqlalchemy import String, Float, Boolean, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin
from app.models.vendor import VendorCategory


class CompliancePolicy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "compliance_policies"

    # ── Which vendor category this policy governs ──────────────
    category: Mapped[VendorCategory] = mapped_column(
        SAEnum(VendorCategory), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Scoring weights (should sum to 1.0; normalized defensively) ─
    weight_status: Mapped[float] = mapped_column(Float, default=0.40, nullable=False)
    weight_documents: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    weight_expiry: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    weight_diversity: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)

    # ── Finding penalties (points deducted per finding, pre-normalization) ─
    finding_penalty_critical: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    finding_penalty_high: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    finding_penalty_medium: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)

    # ── Required document types for full document-completeness credit ─
    # e.g. ["COI", "DIVERSITY_CERT"] — stored as JSON list of DocumentType values
    required_document_types: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # ── Risk tier thresholds — computed score >= threshold -> tier ────
    # A vendor scores 0-100; tier is derived from these cutoffs instead
    # of being a manually-set static field.
    risk_low_min_score: Mapped[float] = mapped_column(Float, default=75.0, nullable=False)
    risk_medium_min_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    # anything below risk_medium_min_score is HIGH risk

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CompliancePolicy category={self.category} name={self.name}>"
