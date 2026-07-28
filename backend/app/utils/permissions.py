# ─────────────────────────────────────────────────────────────
#  app/utils/permissions.py  —  Role-based access control
# ─────────────────────────────────────────────────────────────
"""
Module 4 — Role Based Access.

A single source of truth for what each role may do. Endpoints declare the
*permission* they need rather than hard-coding role names, so adding or
re-scoping a role later means editing one table instead of hunting through
route files.
"""
from enum import Enum
from fastapi import Depends, HTTPException, status

from app.models.user import UserRole


class Permission(str, Enum):
    # Configuration
    CONFIG_VIEW = "config:view"
    CONFIG_EDIT = "config:edit"
    # Vendors
    VENDOR_VIEW_ALL = "vendor:view_all"      # see every vendor
    VENDOR_VIEW_OWN = "vendor:view_own"      # see only your own vendor record
    VENDOR_EDIT = "vendor:edit"
    VENDOR_CREATE = "vendor:create"
    VENDOR_DELETE = "vendor:delete"
    # Documents
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_VIEW_ALL = "document:view_all"
    # Compliance / reporting
    REPORT_VIEW = "report:view"
    ALERT_VIEW = "alert:view"
    # Approvals (Module 9)
    APPROVAL_SUBMIT = "approval:submit"
    APPROVAL_DECIDE = "approval:decide"
    # Audit (Module 7)
    AUDIT_VIEW = "audit:view"
    # User administration
    USER_MANAGE = "user:manage"


# ── Role → permission matrix ──────────────────────────────────
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.CONFIG_VIEW, Permission.CONFIG_EDIT,
        Permission.VENDOR_VIEW_ALL, Permission.VENDOR_EDIT,
        Permission.VENDOR_CREATE, Permission.VENDOR_DELETE,
        Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_VIEW_ALL,
        Permission.REPORT_VIEW, Permission.ALERT_VIEW,
        Permission.APPROVAL_SUBMIT, Permission.APPROVAL_DECIDE,
        Permission.AUDIT_VIEW, Permission.USER_MANAGE,
    },
    UserRole.ANALYST: {
        Permission.CONFIG_VIEW,                       # can see, cannot edit
        Permission.VENDOR_VIEW_ALL, Permission.VENDOR_EDIT,
        Permission.VENDOR_CREATE,
        Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_VIEW_ALL,
        Permission.REPORT_VIEW, Permission.ALERT_VIEW,
        Permission.APPROVAL_SUBMIT,                   # submits, cannot decide
    },
    UserRole.VENDOR: {
        Permission.VENDOR_VIEW_OWN,
        Permission.DOCUMENT_UPLOAD,                   # their own documents
    },
    UserRole.AUDITOR: {
        Permission.CONFIG_VIEW,
        Permission.VENDOR_VIEW_ALL,
        Permission.DOCUMENT_VIEW_ALL,
        Permission.REPORT_VIEW, Permission.ALERT_VIEW,
        Permission.AUDIT_VIEW,
    },
}


def role_of(user) -> UserRole:
    """Resolve a user's role, tolerating legacy records that only set is_admin."""
    role = getattr(user, "role", None)
    if isinstance(role, UserRole):
        return role
    if isinstance(role, str):
        try:
            return UserRole(role)
        except ValueError:
            pass
    return UserRole.ADMIN if getattr(user, "is_admin", False) else UserRole.VENDOR


def has_permission(user, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role_of(user), set())


def permissions_for(user) -> list[str]:
    """All permission strings for a user — sent to the frontend so the UI can
    show or hide features consistently with what the API will actually allow."""
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role_of(user), set()))


def require_permission(permission: Permission):
    """FastAPI dependency factory: guard an endpoint by permission.

    Usage:  _=Depends(require_permission(Permission.CONFIG_EDIT))
    """
    from app.routes.auth import get_current_user

    async def _checker(current_user=Depends(get_current_user)):
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({role_of(current_user).value}) lacks permission: {permission.value}",
            )
        return current_user

    return _checker
