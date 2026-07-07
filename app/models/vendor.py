# ─────────────────────────────────────────────────────────────
#  app/models/vendor.py  —  Vendor ORM model
# ─────────────────────────────────────────────────────────────
import enum
from typing import Optional

from sqlalchemy import String, Float, Integer, ForeignKey, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────
class VendorStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NON_COMPLIANT = "NON_COMPLIANT"


class RiskTier(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ── Model ─────────────────────────────────────────────────────
class Vendor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vendors"

    # ── Identity ──────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Address ───────────────────────────────────────────────
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Compliance ────────────────────────────────────────────
    status: Mapped[VendorStatus] = mapped_column(
        SAEnum(VendorStatus),
        default=VendorStatus.NEEDS_REVIEW,
        nullable=False,
        index=True,
    )
    risk_tier: Mapped[RiskTier] = mapped_column(
        SAEnum(RiskTier),
        default=RiskTier.MEDIUM,
        nullable=False,
        index=True,
    )
    compliance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Diversity certifications (stored as JSON array of strings) ─
    # e.g. ["MBE", "WBE", "DBE"]
    diversity_types: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # ── Insurance expiry dates (ISO strings) ──────────────────
    gl_expiry: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wc_expiry: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Notes ─────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Soft delete ───────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # ── FK → User ─────────────────────────────────────────────
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="vendors", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} name={self.name} status={self.status}>"
