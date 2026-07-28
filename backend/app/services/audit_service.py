# ─────────────────────────────────────────────────────────────
#  app/services/audit_service.py  —  M7 audit trail + M8 versioning
# ─────────────────────────────────────────────────────────────
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditAction, EntityVersion


# Never write these into an audit log or version snapshot.
SENSITIVE_FIELDS = {"hashed_password", "password", "confirm_password", "access_token",
                    "refresh_token", "gemini_api_key", "secret_key"}


def _scrub(data: dict) -> dict:
    return {k: v for k, v in (data or {}).items() if k not in SENSITIVE_FIELDS}


def diff(before: dict, after: dict) -> dict:
    """Field-level changes between two snapshots: {field: {from, to}}."""
    before, after = _scrub(before), _scrub(after)
    out: dict[str, dict] = {}
    for key in set(before) | set(after):
        b, a = before.get(key), after.get(key)
        if b != a:
            out[key] = {"from": b, "to": a}
    return out


def snapshot_of(obj, fields: Optional[list[str]] = None) -> dict:
    """Serialise an ORM object to a plain dict suitable for storage."""
    if obj is None:
        return {}
    if fields is None:
        fields = [c.name for c in obj.__table__.columns]
    out = {}
    for f in fields:
        val = getattr(obj, f, None)
        if hasattr(val, "value"):        # Enum
            val = val.value
        elif hasattr(val, "isoformat"):  # date/datetime
            val = val.isoformat()
        out[f] = val
    return _scrub(out)


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── M7: audit trail ───────────────────────────────────────
    async def log(
        self, action: AuditAction, entity_type: str,
        entity_id: Optional[str] = None, entity_name: Optional[str] = None,
        actor=None, changes: Optional[dict] = None,
        summary: Optional[str] = None, ip_address: Optional[str] = None,
        commit: bool = True,
    ) -> AuditLog:
        from app.utils.permissions import role_of
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            actor_id=getattr(actor, "id", None),
            actor_email=getattr(actor, "email", None),
            actor_role=role_of(actor).value if actor is not None else None,
            changes=_scrub(changes) if changes else None,
            summary=summary,
            ip_address=ip_address,
        )
        self.db.add(entry)
        if commit:
            await self.db.commit()
        return entry

    async def query(
        self, entity_type: Optional[str] = None, entity_id: Optional[str] = None,
        action: Optional[AuditAction] = None, actor_email: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ):
        stmt = select(AuditLog)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if actor_email:
            stmt = stmt.where(AuditLog.actor_email == actor_email)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count(self, **filters) -> int:
        stmt = select(func.count()).select_from(AuditLog)
        if filters.get("entity_type"):
            stmt = stmt.where(AuditLog.entity_type == filters["entity_type"])
        if filters.get("entity_id"):
            stmt = stmt.where(AuditLog.entity_id == filters["entity_id"])
        return (await self.db.execute(stmt)).scalar() or 0

    # ── M8: version history ───────────────────────────────────
    async def record_version(
        self, entity_type: str, entity_id: str, snapshot: dict,
        previous: Optional[dict] = None, actor=None, note: Optional[str] = None,
        commit: bool = True,
    ) -> EntityVersion:
        latest = (await self.db.execute(
            select(func.max(EntityVersion.version_number)).where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )).scalar()
        version = EntityVersion(
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=(latest or 0) + 1,
            snapshot=_scrub(snapshot),
            changes=diff(previous or {}, snapshot) if previous is not None else None,
            changed_by_id=getattr(actor, "id", None),
            changed_by_email=getattr(actor, "email", None),
            change_note=note,
        )
        self.db.add(version)
        if commit:
            await self.db.commit()
            await self.db.refresh(version)
        return version

    async def history(self, entity_type: str, entity_id: str, limit: int = 50):
        stmt = (select(EntityVersion)
                .where(EntityVersion.entity_type == entity_type,
                       EntityVersion.entity_id == entity_id)
                .order_by(EntityVersion.version_number.desc())
                .limit(limit))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_version(self, entity_type: str, entity_id: str, version_number: int):
        stmt = select(EntityVersion).where(
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == entity_id,
            EntityVersion.version_number == version_number,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
