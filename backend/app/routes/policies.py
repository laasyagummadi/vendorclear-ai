# ─────────────────────────────────────────────────────────────
#  app/routes/policies.py  —  Module 9 approval workflow API
# ─────────────────────────────────────────────────────────────
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user
from app.utils.permissions import require_permission, Permission, has_permission
from app.services.approval_service import ApprovalService
from app.models.policy import SubmissionStatus
from app.schemas.policy import (
    PolicyCreate, PolicyUpdate, PolicyOut,
    SubmissionCreate, SubmissionDecision, SubmissionOut,
)

router = APIRouter(prefix="/policies", tags=["policies"])


# ── Policies ──────────────────────────────────────────────────
@router.post("", response_model=PolicyOut, status_code=201,
             summary="Create a compliance policy (admin)")
async def create_policy(
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    svc = ApprovalService(db)
    return await svc.create_policy(data.model_dump(), created_by_id=user.id)


@router.get("", response_model=List[PolicyOut], summary="List compliance policies")
async def list_policies(
    version: Optional[int] = Query(default=None, ge=1, le=2),
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    return await ApprovalService(db).list_policies(version=version, active_only=active_only)


@router.patch("/{policy_id}", response_model=PolicyOut,
              summary="Update a compliance policy (admin)")
async def update_policy(
    policy_id: str,
    data: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    svc = ApprovalService(db)
    policy = await svc.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return await svc.update_policy(policy, data.model_dump(exclude_unset=True))


# ── Submissions ───────────────────────────────────────────────
@router.post("/submissions", response_model=SubmissionOut, status_code=201,
             summary="Submit a vendor against a policy for approval")
async def create_submission(
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # Admin/analyst may submit for anyone; a vendor user only for themselves.
    if not has_permission(user, Permission.APPROVAL_SUBMIT):
        if user.vendor_id != data.vendor_id:
            raise HTTPException(status_code=403, detail="You may only submit for your own vendor.")
    svc = ApprovalService(db)
    try:
        return await svc.create_submission(
            vendor_id=data.vendor_id, policy_id=data.policy_id,
            submitted_by_id=user.id, document_ids=data.document_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/submissions", response_model=List[SubmissionOut],
            summary="List submissions (filter by status)")
async def list_submissions(
    status: Optional[SubmissionStatus] = None,
    vendor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # Vendors only ever see their own submissions.
    if not has_permission(user, Permission.VENDOR_VIEW_ALL):
        vendor_id = user.vendor_id
        if not vendor_id:
            return []
    return await ApprovalService(db).list_submissions(status=status, vendor_id=vendor_id)


@router.get("/submissions/{submission_id}", response_model=SubmissionOut,
            summary="Get one submission")
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    sub = await ApprovalService(db).get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not has_permission(user, Permission.VENDOR_VIEW_ALL) and user.vendor_id != sub.vendor_id:
        raise HTTPException(status_code=403, detail="You may only view your own submissions.")
    return sub


# ── Decisions (ADMIN only) ────────────────────────────────────
@router.post("/submissions/{submission_id}/approve", response_model=SubmissionOut,
             summary="Approve a submission (admin only)")
async def approve_submission(
    submission_id: str,
    data: SubmissionDecision,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(Permission.APPROVAL_DECIDE)),
):
    svc = ApprovalService(db)
    sub = await svc.get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        return await svc.transition(sub, SubmissionStatus.APPROVED,
                                    reviewer_id=user.id, notes=data.notes)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut,
             summary="Reject a submission (admin only)")
async def reject_submission(
    submission_id: str,
    data: SubmissionDecision,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(Permission.APPROVAL_DECIDE)),
):
    svc = ApprovalService(db)
    sub = await svc.get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        return await svc.transition(sub, SubmissionStatus.REJECTED,
                                    reviewer_id=user.id, notes=data.notes)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
