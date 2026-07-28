# ─────────────────────────────────────────────────────────────
#  app/models/user.py  —  User ORM model
# ─────────────────────────────────────────────────────────────
import enum
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """Application roles (Module 4 — Role Based Access).

    ADMIN   — full control: configuration, approvals, user/vendor management.
    ANALYST — day-to-day operator: manages vendors and documents, reviews
              compliance, but cannot change configuration or approve policies.
    VENDOR  — external party: read-only access to *their own* vendor record
              and settings; may upload their own documents.
    AUDITOR — read-only across the whole system for compliance review; can
              see everything but change nothing.
    """
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VENDOR = "VENDOR"
    AUDITOR = "AUDITOR"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Flags ─────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Role (ADMIN / VENDOR) ─────────────────────────────────
    # is_admin is retained for backward compatibility and kept in sync with
    # role; role is the authoritative field going forward.
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.VENDOR, nullable=False, index=True
    )

    # ── Optional link: a VENDOR user → their vendor record ────
    # When set, this user is a vendor and may only view that vendor's data.
    vendor_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("vendors.id", ondelete="SET NULL", use_alter=True, name="fk_user_vendor"),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────
    vendors: Mapped[list["Vendor"]] = relationship(  # noqa: F821
        "Vendor",
        back_populates="created_by",
        lazy="selectin",
        foreign_keys="Vendor.created_by_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
