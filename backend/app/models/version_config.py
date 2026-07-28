# ─────────────────────────────────────────────────────────────
#  app/models/version_config.py  —  Per-version app configuration
# ─────────────────────────────────────────────────────────────
from sqlalchemy import Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class VersionConfig(Base, UUIDMixin, TimestampMixin):
    """
    The admin-editable configuration for a single application version.

    There is exactly one row per version (1 and 2). `settings` is a flat
    JSON object of the configurable parameters (see app/config_defaults.py).
    Storing settings as JSON means new configurable parameters can be added
    later with no schema migration.
    """
    __tablename__ = "version_configs"

    version: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<VersionConfig version={self.version}>"
