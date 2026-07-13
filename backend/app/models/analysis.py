# ─────────────────────────────────────────────────────────────
#  app/models/analysis.py  —  Analysis ORM model (Hruthi)
# ─────────────────────────────────────────────────────────────
import enum
from typing import Optional

from sqlalchemy import String, Float, Boolean, ForeignKey, Enum as SAEnum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class AnalysisStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NON_COMPLIANT = "NON_COMPLIANT"


class Analysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analyses"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Raw OCR / extracted text
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus), default=AnalysisStatus.NEEDS_REVIEW, nullable=False, index=True
    )

    # ── COI-specific fields ────────────────────────────────────
    insured_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    insurer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    policy_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    general_liability_limit_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    workers_comp_limit_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_liability_limit_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    effective_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    expiry_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    additional_insured: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    certificate_holder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Diversity Certificate-specific fields ──────────────────
    cert_body: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cert_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cert_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ownership_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Relationships ──────────────────────────────────────────
    document = relationship("Document", back_populates="analyses")
    findings = relationship("Finding", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} status={self.status} confidence={self.confidence_score}>"
