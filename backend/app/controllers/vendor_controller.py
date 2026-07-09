# ─────────────────────────────────────────────────────────────
#  app/controllers/vendor_controller.py  —  Vendor business logic
# ─────────────────────────────────────────────────────────────
import math
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.vendor_repository import VendorRepository
from app.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorResponse,
    VendorFilterParams, VendorSummary,
)
from app.schemas.common import PaginatedResponse
from app.utils.exceptions import NotFoundError


class VendorController:
    def __init__(self, db: AsyncSession):
        self.repo = VendorRepository(db)

    # ── Create ────────────────────────────────────────────────
    async def create_vendor(
        self, data: VendorCreate, created_by_id: str
    ) -> VendorResponse:
        vendor = await self.repo.create(data, created_by_id=created_by_id)
        logger.info(f"Vendor created: {vendor.name} (id={vendor.id})")
        return VendorResponse.model_validate(vendor)

    # ── Get one ───────────────────────────────────────────────
    async def get_vendor(self, vendor_id: str) -> VendorResponse:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor")
        return VendorResponse.model_validate(vendor)

    # ── List (paginated + filtered) ───────────────────────────
    async def list_vendors(
        self, filters: VendorFilterParams
    ) -> PaginatedResponse[VendorResponse]:
        vendors, total = await self.repo.get_all(filters)
        total_pages = math.ceil(total / filters.page_size) if total else 1

        return PaginatedResponse(
            data=[VendorResponse.model_validate(v) for v in vendors],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    # ── Update ────────────────────────────────────────────────
    async def update_vendor(
        self, vendor_id: str, data: VendorUpdate
    ) -> VendorResponse:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor")

        vendor = await self.repo.update(vendor, data)
        logger.info(f"Vendor updated: {vendor.name} (id={vendor.id})")
        return VendorResponse.model_validate(vendor)

    # ── Delete (soft) ─────────────────────────────────────────
    async def delete_vendor(self, vendor_id: str) -> dict:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor")

        await self.repo.soft_delete(vendor)
        logger.info(f"Vendor soft-deleted: {vendor.name} (id={vendor.id})")
        return {"message": f"Vendor '{vendor.name}' deleted successfully"}

    # ── Expiring soon ─────────────────────────────────────────
    async def get_expiring_soon(self, days: int = 30) -> list[VendorSummary]:
        vendors = await self.repo.get_expiring_soon(days)
        return [VendorSummary.model_validate(v) for v in vendors]

    # ── Status breakdown (for dashboard) ─────────────────────
    async def get_status_summary(self) -> dict:
        counts = await self.repo.count_by_status()
        return {
            "compliant": counts.get("COMPLIANT", 0),
            "needs_review": counts.get("NEEDS_REVIEW", 0),
            "non_compliant": counts.get("NON_COMPLIANT", 0),
            "total": sum(counts.values()),
        }
