# ─────────────────────────────────────────────────────────────
#  app/routes/scoring_policies.py  —  Compliance policy admin endpoints
# ─────────────────────────────────────────────────────────────
"""
Admin-configurable per-category compliance scoring policies.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.utils.rbac import require_roles
from app.models.user import User, UserRole
from app.controllers.policy_controller import PolicyController
from app.schemas.policy import (
    CompliancePolicyCreate, CompliancePolicyUpdate, CompliancePolicyResponse,
)
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/scoring-policies", tags=["compliance-policies"])


@router.get(
    "",
    response_model=list[CompliancePolicyResponse],
    summary="List all compliance policies (one per vendor category)",
)
async def list_policies(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = PolicyController(db)
    return await ctrl.list_policies()


@router.get(
    "/{policy_id}",
    response_model=CompliancePolicyResponse,
    summary="Get a single compliance policy",
)
async def get_policy(
    policy_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = PolicyController(db)
    return await ctrl.get_policy(policy_id)


@router.post(
    "",
    response_model=CompliancePolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a compliance policy for a category that doesn't have one yet",
)
async def create_policy(
    data: CompliancePolicyCreate,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    ctrl = PolicyController(db)
    return await ctrl.create_policy(data)


@router.patch(
    "/{policy_id}",
    response_model=CompliancePolicyResponse,
    summary="Update a compliance policy's weights, penalties, or thresholds",
)
async def update_policy(
    policy_id: str,
    data: CompliancePolicyUpdate,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    ctrl = PolicyController(db)
    return await ctrl.update_policy(policy_id, data)


@router.delete(
    "/{policy_id}",
    response_model=SuccessResponse,
    summary="Delete a compliance policy (that category reverts to the bootstrap default)",
)
async def delete_policy(
    policy_id: str,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    ctrl = PolicyController(db)
    result = await ctrl.delete_policy(policy_id)
    return SuccessResponse(message=result["message"])
