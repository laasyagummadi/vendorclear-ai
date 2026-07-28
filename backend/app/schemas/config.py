# ─────────────────────────────────────────────────────────────
#  app/schemas/config.py  —  Config & admin request/response models
# ─────────────────────────────────────────────────────────────
from typing import Any, Optional
from pydantic import BaseModel, Field


class ConfigUpdateRequest(BaseModel):
    """Partial update of a version's configuration."""
    settings: dict[str, Any] = Field(
        ..., description="Partial map of {config_key: value} to update."
    )
    apply_to_existing: bool = Field(
        default=False,
        description="If true, overwrite the effective config of all existing "
                    "vendors on this version (requirement 5).",
    )


class ConfigUpdateResponse(BaseModel):
    version: int
    settings: dict[str, Any]
    applied_to_existing: bool
    vendors_updated: int


class VersionAssignRequest(BaseModel):
    version: int = Field(..., ge=1, le=2)


class VendorConfigView(BaseModel):
    """What a vendor is allowed to see about their own settings."""
    vendor_id: str
    vendor_name: str
    assigned_version: int
    effective_config: dict[str, Any]
