# ─────────────────────────────────────────────────────────────
#  config.py  —  Application settings (pydantic-settings)
# ─────────────────────────────────────────────────────────────
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    app_name: str = "VendorClear AI"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "vendorclear_db"

    # ── JWT ───────────────────────────────────────────────────
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── CORS ──────────────────────────────────────────────────
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── SQLite dev mode ───────────────────────────────────────
    # Set USE_SQLITE=true in .env for zero-config local dev (no MySQL)
    use_sqlite: bool = False

    # ── Hosted database (deployment) ──────────────────────────
    # Most hosting platforms (Render, Railway, Fly, Heroku, Neon) provide
    # a DATABASE_URL env var for their managed database. When set, it
    # takes priority over both USE_SQLITE and the DB_* MySQL settings.
    # postgres:// / postgresql:// / mysql:// URLs are all accepted and
    # normalized to their async drivers automatically.
    database_url_env: str = Field(default="", alias="DATABASE_URL")

    # ── Gemini AI ─────────────────────────────────────────────
    gemini_api_key: str = ""

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    @staticmethod
    def _to_async_url(url: str) -> str:
        """Normalize a generic DB URL to its async SQLAlchemy driver."""
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        return url

    @staticmethod
    def _to_sync_url(url: str) -> str:
        """Normalize a generic DB URL to a sync driver (for Alembic)."""
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://", 1)
        return url

    @property
    def database_url(self) -> str:
        """Async connection URL for SQLAlchemy, in priority order:
        DATABASE_URL env var > SQLite dev mode > DB_* MySQL settings."""
        if self.database_url_env:
            return self._to_async_url(self.database_url_env)
        if self.use_sqlite:
            return "sqlite+aiosqlite:///./vendorclear.db"
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic migrations, same priority order."""
        if self.database_url_env:
            return self._to_sync_url(self.database_url_env)
        if self.use_sqlite:
            return "sqlite:///./vendorclear.db"
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
