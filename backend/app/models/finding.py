# ─────────────────────────────────────────────────────────────
#  app/models/finding.py  —  Finding ORM model (Hruthi)
# ─────────────────────────────────────────────────────────────
import enum

from sqlalchemy import String, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class FindingSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Finding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "findings"

    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        SAEnum(FindingSeverity), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    analysis = relationship("Analysis", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding id={self.id} severity={self.severity} rule={self.rule_code}>"
