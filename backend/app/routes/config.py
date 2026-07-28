# ─────────────────────────────────────────────────────────────
#  app/routes/config.py  —  Admin configuration + vendor config view
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import require_admin, get_current_user
from app.utils.permissions import require_permission, Permission
from app.services.config_service import ConfigService
from app.schemas.config import (
    ConfigUpdateRequest, ConfigUpdateResponse,
    VersionAssignRequest, VendorConfigView,
)
from app.models.vendor import Vendor

router = APIRouter(prefix="/config", tags=["config"])


# ── Read all version configs (admin, analyst, auditor) ────────
@router.get("/versions", summary="Get all version configurations")
async def get_all_configs(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    svc = ConfigService(db)
    await svc.ensure_seeded()
    return await svc.get_all_configs()


# ── Read one version config ───────────────────────────────────
@router.get("/versions/{version}", summary="Get one version's configuration")
async def get_version_config(
    version: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    if version not in (1, 2):
        raise HTTPException(status_code=404, detail="Version must be 1 or 2.")
    svc = ConfigService(db)
    return {"version": version, "settings": await svc.get_config(version)}


# ── Update a version config (ADMIN only) ──────────────────────
@router.put(
    "/versions/{version}",
    response_model=ConfigUpdateResponse,
    summary="Update a version's configuration (admin only)",
)
async def update_version_config(
    version: int,
    data: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if version not in (1, 2):
        raise HTTPException(status_code=404, detail="Version must be 1 or 2.")
    svc = ConfigService(db)
    try:
        return await svc.update_config(
            version, data.settings, apply_to_existing=data.apply_to_existing,
            actor=user,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Assign a vendor to a version (ADMIN only) ─────────────────
@router.put(
    "/vendors/{vendor_id}/version",
    summary="Assign a vendor to a version (admin only)",
)
async def assign_vendor_version(
    vendor_id: str,
    data: VersionAssignRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")
    svc = ConfigService(db)
    try:
        vendor = await svc.assign_vendor_version(vendor, data.version)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "vendor_id": vendor.id,
        "assigned_version": vendor.assigned_version,
        "effective_config": vendor.effective_config,
    }


# ── Vendor (or admin): read the effective config for a vendor ─
@router.get(
    "/vendors/{vendor_id}/effective",
    response_model=VendorConfigView,
    summary="View the settings that apply to a vendor (read-only)",
)
async def get_vendor_effective_config(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.utils.permissions import has_permission, Permission
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    # A user who can only view their OWN vendor (the VENDOR role) is blocked
    # from reading anyone else's settings (requirement 6 / Module 4).
    if not has_permission(current_user, Permission.VENDOR_VIEW_ALL):
        if current_user.vendor_id != vendor_id:
            raise HTTPException(status_code=403, detail="You may only view your own settings.")

    svc = ConfigService(db)
    effective = await svc.get_effective_config(vendor)
    return VendorConfigView(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        assigned_version=vendor.assigned_version or 1,
        effective_config=effective,
    )
