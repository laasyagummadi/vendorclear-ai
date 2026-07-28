# ─────────────────────────────────────────────────────────────
#  app/models/user.py  —  User ORM model
# ─────────────────────────────────────────────────────────────
import enum

from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """Feature 7 — Role-Based Access Control.

    ADMIN    — complete access: manage vendors, approve changes, manage
               policies, view reports.
    ANALYST  — review AI results, approve compliance, generate reports.
    VENDOR   — upload documents, view own compliance, download reports,
               receive alerts. Cannot manage policies or other vendors.
    AUDITOR  — read-only: view history, export reports. No editing rights
               anywhere in the system.
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
    # NOTE: is_admin is kept for backward compatibility with existing code/
    # tests that check it directly, but it is now derived from `role` at
    # creation/update time (see UserRepository) rather than being the
    # source of truth. `role` is the source of truth for permissions.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.ANALYST, nullable=False, index=True
    )

    # ── Relationships ─────────────────────────────────────────
    vendors: Mapped[list["Vendor"]] = relationship(  # noqa: F821
        "Vendor",
        back_populates="created_by",
        foreign_keys="[Vendor.created_by_id]",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
