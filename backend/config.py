# ─────────────────────────────────────────────────────────────
#  config.py  —  Application settings (pydantic-settings)
# ─────────────────────────────────────────────────────────────
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import List

logger = logging.getLogger("vendorclear.config")


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
    # a DATABASE_URL env var for their managed database. When set (and
    # non-blank), it takes priority over both USE_SQLITE and the DB_*
    # MySQL settings. postgres:// / postgresql:// / mysql:// URLs are all
    # accepted and normalized to their async drivers automatically.
    #
    # NOTE: pydantic-settings reads this from the real OS environment
    # variable DATABASE_URL *in addition to* .env — if you have a stray
    # DATABASE_URL set in your shell/session/System Environment Variables
    # (e.g. left over from testing a deployment), it WILL silently win
    # here even if .env has USE_SQLITE=true. Run this in PowerShell to
    # check: echo $env:DATABASE_URL  — if that prints anything, remove it
    # with Remove-Item Env:DATABASE_URL (current session) or via
    # "Edit environment variables for your account" (permanently).
    database_url_env: str = Field(default="", alias="DATABASE_URL")

    # ── Gemini AI ─────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Email / SMTP (vendor alert notifications) ─────────────
    # Works with any generic SMTP provider (Gmail, Outlook/Office365,
    # Zoho, a corporate relay, etc). For Gmail/Outlook you'll typically
    # need an "app password" rather than your normal login password.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True          # STARTTLS (port 587). Set false + smtp_port=465 for implicit TLS/SSL.
    smtp_from_email: str = ""          # defaults to smtp_user if left blank
    smtp_from_name: str = "VendorClear AI"

    # ── Vendor alert notifications ────────────────────────────
    # Master switch — if false, the scheduled job and manual "Notify
    # Vendors" endpoint both no-op (useful for local dev without SMTP set up).
    alerts_email_enabled: bool = False
    # How many days ahead to scan for expiring insurance when the
    # scheduler runs (same look-ahead window as the Alerts page default).
    alert_expiry_lookahead_days: int = 30
    # Hour of day (0-23, server local time) the daily scheduled job runs.
    alert_schedule_hour: int = 8

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    @field_validator("database_url_env", mode="before")
    @classmethod
    def strip_blank_database_url(cls, v):
        """Treat a whitespace-only DATABASE_URL as unset, so it can't
        silently override USE_SQLITE due to a stray blank env var."""
        if v is None:
            return ""
        v = str(v).strip()
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


def _masked(url: str) -> str:
    """Mask password/credentials before logging a DB URL."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            creds, host_part = rest.rsplit("@", 1)
            return f"{scheme}://***:***@{host_part}"
    return url


settings = Settings()

# ── Startup visibility ─────────────────────────────────────────
# Logs which database this process actually resolved to, and why,
# so "why is my data missing" can be diagnosed from the console
# instead of guessing. This is the single most useful line for
# debugging environment/DB-mismatch issues.
if settings.database_url_env:
    _source = "DATABASE_URL env var"
elif settings.use_sqlite:
    _source = "USE_SQLITE=true"
else:
    _source = "DB_* MySQL settings"

logger.warning(
    "DB config resolved via %s -> %s", _source, _masked(settings.database_url)
)
print(f"[config] Database source: {_source}")
print(f"[config] Resolved database_url: {_masked(settings.database_url)}")