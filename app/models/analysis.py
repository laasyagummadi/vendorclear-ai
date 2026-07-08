import enum
from sqlalchemy import String, Float, Boolean, ForeignKey, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class AnalysisStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NON_COMPLIANT = "NON_COMPLIANT"

class Analysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analyses"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # ── Core Analysis Metadata ────────────────────────────────
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus), default=AnalysisStatus.NEEDS_REVIEW, nullable=False
    )

    # ── COI Extracted Fields ──────────────────────────────────
    insured_name: Mapped[str] = mapped_column(String(255), nullable=True)
    insurer_name: Mapped[str] = mapped_column(String(255), nullable=True)
    policy_number: Mapped[str] = mapped_column(String(100), nullable=True)
    coverage_type: Mapped[str] = mapped_column(String(100), nullable=True)
    general_liability_limit_usd: Mapped[float] = mapped_column(Float, nullable=True)
    workers_comp_limit_usd: Mapped[float] = mapped_column(Float, nullable=True)
    auto_liability_limit_usd: Mapped[float] = mapped_column(Float, nullable=True)
    effective_date: Mapped[str] = mapped_column(String(20), nullable=True)
    expiry_date: Mapped[str] = mapped_column(String(20), nullable=True)
    additional_insured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    certificate_holder: Mapped[str] = mapped_column(String(255), nullable=True)

    # ── Diversity Cert Extracted Fields ───────────────────────
    cert_body: Mapped[str] = mapped_column(String(255), nullable=True)
    cert_type: Mapped[str] = mapped_column(String(100), nullable=True)
    cert_number: Mapped[str] = mapped_column(String(100), nullable=True)
    ownership_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Relationships ─────────────────────────────────────────
    document = relationship("Document", back_populates="analyses")
    findings = relationship("Finding", back_populates="analysis", cascade="all, delete-orphan")
