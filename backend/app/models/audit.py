# ─────────────────────────────────────────────────────────────
#  app/models/audit.py  —  Audit trail (M7) + version history (M8)
# ─────────────────────────────────────────────────────────────
import enum
from typing import Optional

from sqlalchemy import String, Integer, JSON, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    UPLOAD = "UPLOAD"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    VERSION_ASSIGN = "VERSION_ASSIGN"


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Module 7 — Audit Trail. One row per significant action.

    Deliberately denormalised (actor_email, entity_name captured at write
    time) so the log stays readable even after the referenced user or
    record is deleted — an audit trail that breaks when data is removed
    is not an audit trail.
    """
    __tablename__ = "audit_logs"

    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # What actually changed: {"field": {"from": x, "to": y}}
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}:{self.entity_id}>"


class EntityVersion(Base, UUIDMixin, TimestampMixin):
    """
    Module 8 — Version History. A point-in-time snapshot of an entity.

    Stores version number, who changed it, when, and the full snapshot plus
    a diff from the previous version, so history can be listed and any
    version inspected or restored.
    """
    __tablename__ = "entity_versions"

    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    changed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_by_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    change_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<EntityVersion {self.entity_type}:{self.entity_id} v{self.version_number}>"
