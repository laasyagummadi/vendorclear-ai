# ─────────────────────────────────────────────────────────────
#  app/utils/rbac.py  —  Role-Based Access Control (Feature 7)
# ─────────────────────────────────────────────────────────────
"""
Sprint Day 1 (20 July) deliverable — Laasya.

Adds real role enforcement on top of the existing JWT auth. Previously
every authenticated user (regardless of role) could hit every endpoint,
including admin-only actions like creating/editing/deleting compliance
policies or deleting vendors.

Roles (see app.models.user.UserRole):
    ADMIN   — full access
    ANALYST — review AI results, approve compliance, generate reports
    VENDOR  — upload documents, view own compliance, receive alerts
    AUDITOR — read-only everywhere, no editing rights

Usage in a route:

    from app.utils.rbac import require_roles
    from app.models.user import UserRole

    @router.delete("/{vendor_id}")
    async def delete_vendor(
        vendor_id: str,
        user: User = Depends(require_roles(UserRole.ADMIN)),
        db: AsyncSession = Depends(get_db),
    ):
        ...
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.routes.auth import get_current_user_id
from app.utils.exceptions import AuthenticationError, AuthorizationError


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the full User row (not just the id) for the caller's token."""
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Account is deactivated. Contact support.")
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory: only lets callers whose role is in `allowed_roles`
    reach the route. Raises 403 (not 401 — the caller *is* authenticated,
    they're just not permitted to perform this specific action)."""

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            allowed = ", ".join(r.value for r in allowed_roles)
            raise AuthorizationError(
                f"Your role ({user.role.value}) does not have permission "
                f"to perform this action. Requires: {allowed}."
            )
        return user

    return _dependency
