# ─────────────────────────────────────────────────────────────
#  app/models/policy.py  —  Compliance policies & approval workflow
# ─────────────────────────────────────────────────────────────
"""
Module 9 — Approval Workflow.

Flow:
    Admin creates a CompliancePolicy   e.g. "Construction Policy"
        requirements: GL $5,000,000, Workers Comp required, Umbrella required
    Vendor (or analyst) submits documents against that policy
        → PolicySubmission created with status PENDING
    Admin reviews
        → APPROVED  → submission becomes ACTIVE for the vendor
        → REJECTED  → vendor must resubmit
"""
import enum
from typing import Optional

from sqlalchemy import String, Integer, Boolean, JSON, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class SubmissionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"        # awaiting admin decision
    APPROVED = "APPROVED"      # admin approved
    REJECTED = "REJECTED"      # admin rejected, vendor may resubmit
    ACTIVE = "ACTIVE"          # approved and currently in force
    EXPIRED = "EXPIRED"        # was active, now lapsed


class CompliancePolicy(Base, UUIDMixin, TimestampMixin):
    """
    An admin-defined set of compliance requirements a vendor must satisfy,
    e.g. "Construction Policy" requiring $5M GL + Workers Comp + Umbrella.

    `requirements` is a JSON object so new requirement types can be added
    without a schema migration, consistent with the version-config design.
    Example:
        {
          "required_gl_limit_usd": 5000000,
          "workers_comp_required": true,
          "umbrella_required": true,
          "umbrella_limit_usd": 3000000
        }
    """
    __tablename__ = "compliance_policies"

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

    submissions: Mapped[list["PolicySubmission"]] = relationship(
        "PolicySubmission", back_populates="policy",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CompliancePolicy {self.name} v{self.version}>"


class PolicySubmission(Base, UUIDMixin, TimestampMixin):
    """
    A vendor's submission against a policy, moving through the approval
    state machine. Holds the reviewer's decision and notes for audit.
    """
    __tablename__ = "policy_submissions"

    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_policies.id", ondelete="CASCADE"),
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

    policy: Mapped["CompliancePolicy"] = relationship(
        "CompliancePolicy", back_populates="submissions", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PolicySubmission vendor={self.vendor_id} status={self.status}>"
