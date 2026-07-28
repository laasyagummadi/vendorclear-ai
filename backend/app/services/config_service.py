# ─────────────────────────────────────────────────────────────
#  app/services/config_service.py  —  Version configuration engine
# ─────────────────────────────────────────────────────────────
"""
Manages admin-editable, version-specific application configuration and the
per-vendor config snapshots (Option A).

Key behaviors:
- Two VersionConfig rows exist (version 1 and 2), seeded from defaults.
- Each vendor holds an `effective_config` snapshot + an `assigned_version`.
- When the admin updates a version's config they choose whether to
  "apply to existing vendors" of that version:
    * apply=True  → overwrite every existing vendor's snapshot for that version
    * apply=False → only the version config changes; existing vendors keep
                    their snapshot; newly assigned vendors get the new config.
"""
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version_config import VersionConfig
from app.models.vendor import Vendor
from app.config_defaults import DEFAULTS_BY_VERSION, coerce_value, CONFIG_SCHEMA


class ConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Seeding ───────────────────────────────────────────────
    async def ensure_seeded(self) -> None:
        """Create the version 1 & 2 config rows from defaults if absent."""
        for version, defaults in DEFAULTS_BY_VERSION.items():
            existing = await self._get_row(version)
            if not existing:
                self.db.add(VersionConfig(version=version, settings=dict(defaults)))
        await self.db.commit()

    async def _get_row(self, version: int) -> Optional[VersionConfig]:
        result = await self.db.execute(
            select(VersionConfig).where(VersionConfig.version == version)
        )
        return result.scalar_one_or_none()

    # ── Read ──────────────────────────────────────────────────
    async def get_config(self, version: int) -> dict:
        """Return the current settings for a version (seed on demand)."""
        row = await self._get_row(version)
        if not row:
            defaults = DEFAULTS_BY_VERSION.get(version, DEFAULTS_BY_VERSION[1])
            row = VersionConfig(version=version, settings=dict(defaults))
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
        return dict(row.settings)

    async def get_all_configs(self) -> dict:
        return {
            "version_1": await self.get_config(1),
            "version_2": await self.get_config(2),
            "schema": {
                k: {"label": v[0], "type": v[1], "help": v[2]}
                for k, v in CONFIG_SCHEMA.items()
            },
        }

    # ── Update ────────────────────────────────────────────────
    async def update_config(
        self,
        version: int,
        updates: dict[str, Any],
        apply_to_existing: bool = False,
        actor=None,
    ) -> dict:
        """
        Update a version's configuration.

        `updates` is a partial dict of {config_key: value}; unknown keys are
        rejected and values are coerced to their declared type.

        If `apply_to_existing` is True, every existing vendor on this version
        has their effective_config snapshot overwritten with the new config.
        """
        row = await self._get_row(version)
        if not row:
            await self.ensure_seeded()
            row = await self._get_row(version)

        previous = dict(row.settings)
        merged = dict(row.settings)
        for key, value in updates.items():
            if key not in CONFIG_SCHEMA:
                raise ValueError(f"Unknown configuration key: {key}")
            merged[key] = coerce_value(key, value)

        row.settings = merged
        self.db.add(row)

        applied_count = 0
        if apply_to_existing:
            applied_count = await self._apply_to_existing_vendors(version, merged)

        # M7 audit trail + M8 version history for every configuration change.
        from app.services.audit_service import AuditService, diff
        from app.models.audit import AuditAction
        audit = AuditService(self.db)
        changed = diff(previous, merged)
        await audit.log(
            AuditAction.CONFIG_CHANGE, "version_config",
            entity_id=row.id, entity_name=f"Version {version} configuration",
            actor=actor, changes=changed,
            summary=(f"Updated {len(changed)} setting(s) on Version {version}"
                     + (f"; applied to {applied_count} existing vendor(s)" if apply_to_existing else "")),
            commit=False,
        )
        await audit.record_version(
            "version_config", row.id, merged, previous=previous, actor=actor,
            note=f"Config update (apply_to_existing={apply_to_existing})",
            commit=False,
        )

        await self.db.commit()
        return {
            "version": version,
            "settings": merged,
            "applied_to_existing": apply_to_existing,
            "vendors_updated": applied_count,
        }

    async def _apply_to_existing_vendors(self, version: int, config: dict) -> int:
        """Overwrite the effective_config snapshot of every active vendor
        assigned to this version. Returns the count updated."""
        result = await self.db.execute(
            select(Vendor).where(
                Vendor.assigned_version == version,
                Vendor.is_active == True,  # noqa: E712
            )
        )
        vendors = list(result.scalars().all())
        for v in vendors:
            v.effective_config = dict(config)
            self.db.add(v)
        return len(vendors)

    # ── Vendor assignment ─────────────────────────────────────
    async def assign_vendor_version(self, vendor: Vendor, version: int) -> Vendor:
        """Assign a vendor to a version and snapshot that version's current
        config onto the vendor (their starting effective_config)."""
        if version not in DEFAULTS_BY_VERSION:
            raise ValueError(f"Invalid version: {version}")
        config = await self.get_config(version)
        vendor.assigned_version = version
        vendor.effective_config = dict(config)
        self.db.add(vendor)
        await self.db.commit()
        await self.db.refresh(vendor)
        return vendor

    async def get_effective_config(self, vendor: Vendor) -> dict:
        """The settings that actually apply to a vendor. Falls back to their
        version's current config if no snapshot exists yet."""
        if vendor.effective_config:
            return dict(vendor.effective_config)
        return await self.get_config(vendor.assigned_version or 1)
