# ─────────────────────────────────────────────────────────────
#  app/models/policy.py  —  Compliance & Approval Policies
# ─────────────────────────────────────────────────────────────
import enum
from typing import Optional

from sqlalchemy import String, Float, Integer, Boolean, Enum as SAEnum, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin
from app.models.vendor import VendorCategory


class CompliancePolicy(Base, UUIDMixin, TimestampMixin):
    """
    An admin-configurable scoring policy, one per vendor category
    (Construction / Software / Electrical / Other). Replaces the old
    hardcoded WEIGHT_STATUS / WEIGHT_DOCUMENTS / WEIGHT_EXPIRY /
    WEIGHT_DIVERSITY constants that used to be applied identically to
    every vendor regardless of category.
    """
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
    risk_low_min_score: Mapped[float] = mapped_column(Float, default=75.0, nullable=False)
    risk_medium_min_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CompliancePolicy category={self.category} name={self.name}>"


# ── Approval Workflow ─────────────────────────────────────────

class SubmissionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"        # awaiting admin decision
    APPROVED = "APPROVED"      # admin approved
    REJECTED = "REJECTED"      # admin rejected, vendor may resubmit
    ACTIVE = "ACTIVE"          # approved and currently in force
    EXPIRED = "EXPIRED"        # was active, now lapsed


class ApprovalPolicy(Base, UUIDMixin, TimestampMixin):
    """
    An admin-defined set of compliance requirements a vendor must satisfy,
    e.g. "Construction Policy" requiring $5M GL + Workers Comp + Umbrella.
    """
    __tablename__ = "approval_policies"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Which application version this policy belongs to (1 or 2).
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)

    requirements: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    submissions: Mapped[list["ApprovalSubmission"]] = relationship(
        "ApprovalSubmission", back_populates="policy",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ApprovalPolicy {self.name} v{self.version}>"


class ApprovalSubmission(Base, UUIDMixin, TimestampMixin):
    """
    A vendor's submission against an ApprovalPolicy, moving through the approval
    state machine. Holds the reviewer's decision and notes for audit.
    """
    __tablename__ = "approval_submissions"

    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("approval_policies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus), default=SubmissionStatus.PENDING,
        nullable=False, index=True,
    )

    # Which documents the vendor attached to this submission
    document_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Automated check of the submission against the policy requirements
    requirement_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meets_requirements: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    submitted_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # ── Review / decision ─────────────────────────────────────
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    policy: Mapped["ApprovalPolicy"] = relationship(
        "ApprovalPolicy", back_populates="submissions", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ApprovalSubmission vendor={self.vendor_id} status={self.status}>"
