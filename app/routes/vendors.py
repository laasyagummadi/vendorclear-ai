# ─────────────────────────────────────────────────────────────
#  app/routes/vendors.py  —  Vendor CRUD endpoints
# ─────────────────────────────────────────────────────────────
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.controllers.vendor_controller import VendorController
from app.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorResponse,
    VendorFilterParams, VendorSummary,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.models.vendor import VendorStatus, RiskTier

router = APIRouter(prefix="/vendors", tags=["vendors"])


# ── Create ────────────────────────────────────────────────────
@router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new vendor",
)
async def create_vendor(
    data: VendorCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    return await ctrl.create_vendor(data, created_by_id=user_id)


# ── List (paginated + filtered) ───────────────────────────────
@router.get(
    "",
    response_model=PaginatedResponse[VendorResponse],
    summary="List vendors with optional filters and pagination",
)
async def list_vendors(
    status_filter: Optional[VendorStatus] = Query(None, alias="status"),
    risk_tier: Optional[RiskTier] = Query(None),
    search: Optional[str] = Query(None, description="Search by name, email, or contact"),
    is_active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    filters = VendorFilterParams(
        status=status_filter,
        risk_tier=risk_tier,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    ctrl = VendorController(db)
    return await ctrl.list_vendors(filters)


# ── Get one ───────────────────────────────────────────────────
@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Get a single vendor by ID",
)
async def get_vendor(
    vendor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    return await ctrl.get_vendor(vendor_id)


# ── Update ────────────────────────────────────────────────────
@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Update vendor details (partial update)",
)
async def update_vendor(
    vendor_id: str,
    data: VendorUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    return await ctrl.update_vendor(vendor_id, data)


# ── Delete ────────────────────────────────────────────────────
@router.delete(
    "/{vendor_id}",
    response_model=SuccessResponse,
    summary="Soft-delete a vendor",
)
async def delete_vendor(
    vendor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    result = await ctrl.delete_vendor(vendor_id)
    return SuccessResponse(message=result["message"])


# ── Special endpoints ─────────────────────────────────────────
@router.get(
    "/alerts/expiring-soon",
    response_model=list[VendorSummary],
    summary="Vendors with insurance expiring in the next N days",
)
async def expiring_soon(
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    return await ctrl.get_expiring_soon(days)


@router.get(
    "/stats/summary",
    summary="Compliance status breakdown for dashboard",
)
async def status_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = VendorController(db)
    return await ctrl.get_status_summary()
