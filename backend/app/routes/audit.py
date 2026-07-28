# ─────────────────────────────────────────────────────────────
#  app/routes/audit.py  —  M7 audit trail + M8 version history API
# ─────────────────────────────────────────────────────────────
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.permissions import require_permission, Permission
from app.services.audit_service import AuditService
from app.models.audit import AuditAction

router = APIRouter(prefix="/audit", tags=["audit"])


def _log_out(row) -> dict:
    return {
        "id": row.id,
        "action": row.action.value if hasattr(row.action, "value") else row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "entity_name": row.entity_name,
        "actor_email": row.actor_email,
        "actor_role": row.actor_role,
        "changes": row.changes,
        "summary": row.summary,
        "timestamp": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/logs", summary="Query the audit trail (admin/auditor)")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[AuditAction] = None,
    actor_email: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.AUDIT_VIEW)),
):
    svc = AuditService(db)
    rows = await svc.query(
        entity_type=entity_type, entity_id=entity_id,
        action=action, actor_email=actor_email, limit=limit, offset=offset,
    )
    total = await svc.count(entity_type=entity_type, entity_id=entity_id)
    return {"total": total, "limit": limit, "offset": offset,
            "logs": [_log_out(r) for r in rows]}


@router.get("/history/{entity_type}/{entity_id}",
            summary="Version history for an entity (admin/auditor)")
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.AUDIT_VIEW)),
):
    versions = await AuditService(db).history(entity_type, entity_id, limit=limit)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "versions": [
            {
                "version": v.version_number,
                "date": v.created_at.isoformat() if v.created_at else None,
                "uploader": v.changed_by_email,
                "changes": v.changes,
                "note": v.change_note,
                "snapshot": v.snapshot,
            }
            for v in versions
        ],
    }


@router.get("/history/{entity_type}/{entity_id}/{version_number}",
            summary="Fetch one historical version (admin/auditor)")
async def get_one_version(
    entity_type: str,
    entity_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.AUDIT_VIEW)),
):
    v = await AuditService(db).get_version(entity_type, entity_id, version_number)
    if not v:
        raise HTTPException(status_code=404, detail="Version not found.")
    return {
        "version": v.version_number,
        "date": v.created_at.isoformat() if v.created_at else None,
        "uploader": v.changed_by_email,
        "changes": v.changes,
        "note": v.change_note,
        "snapshot": v.snapshot,
    }
