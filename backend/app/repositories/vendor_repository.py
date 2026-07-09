# ─────────────────────────────────────────────────────────────
#  app/repositories/vendor_repository.py  —  Vendor DB ops
# ─────────────────────────────────────────────────────────────
import math
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor, VendorStatus, RiskTier
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorFilterParams


class VendorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────
    async def get_by_id(self, vendor_id: str) -> Optional[Vendor]:
        result = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, filters: VendorFilterParams
    ) -> Tuple[List[Vendor], int]:
        """
        Returns (vendors, total_count) applying filters + pagination.
        """
        query = select(Vendor)

        # ── Filters ───────────────────────────────────────────
        if filters.is_active is not None:
            query = query.where(Vendor.is_active == filters.is_active)
        if filters.status:
            query = query.where(Vendor.status == filters.status)
        if filters.risk_tier:
            query = query.where(Vendor.risk_tier == filters.risk_tier)
        if filters.search:
            term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Vendor.name.ilike(term),
                    Vendor.email.ilike(term),
                    Vendor.contact_name.ilike(term),
                )
            )

        # ── Count ─────────────────────────────────────────────
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        # ── Pagination + ordering ─────────────────────────────
        query = (
            query
            .order_by(Vendor.created_at.desc())
            .offset(filters.offset)
            .limit(filters.page_size)
        )
        result = await self.db.execute(query)
        vendors = list(result.scalars().all())

        return vendors, total

    async def get_expiring_soon(self, days: int = 30) -> List[Vendor]:
        """Vendors whose GL or WC insurance expires within `days` days."""
        from datetime import date, timedelta
        today = date.today().isoformat()
        cutoff = (date.today() + timedelta(days=days)).isoformat()

        result = await self.db.execute(
            select(Vendor).where(
                Vendor.is_active == True,
                or_(
                    (Vendor.gl_expiry >= today) & (Vendor.gl_expiry <= cutoff),
                    (Vendor.wc_expiry >= today) & (Vendor.wc_expiry <= cutoff),
                ),
            ).order_by(Vendor.gl_expiry)
        )
        return list(result.scalars().all())

    async def count_by_status(self) -> dict:
        """Returns {status: count} breakdown."""
        result = await self.db.execute(
            select(Vendor.status, func.count(Vendor.id))
            .where(Vendor.is_active == True)
            .group_by(Vendor.status)
        )
        return {row[0]: row[1] for row in result.all()}

    # ── Create ────────────────────────────────────────────────
    async def create(
        self, data: VendorCreate, created_by_id: Optional[str] = None
    ) -> Vendor:
        vendor = Vendor(
            **data.model_dump(exclude_none=True),
            created_by_id=created_by_id,
        )
        self.db.add(vendor)
        await self.db.flush()
        await self.db.refresh(vendor)
        return vendor

    # ── Update ────────────────────────────────────────────────
    async def update(self, vendor: Vendor, data: VendorUpdate) -> Vendor:
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(vendor, field, value)
        await self.db.flush()
        await self.db.refresh(vendor)
        return vendor

    # ── Soft delete ───────────────────────────────────────────
    async def soft_delete(self, vendor: Vendor) -> Vendor:
        vendor.is_active = False
        await self.db.flush()
        return vendor

    # ── Compliance update (called by Hruthi's analysis layer) ─
    async def update_compliance(
        self,
        vendor: Vendor,
        score: float,
        status: VendorStatus,
        risk_tier: RiskTier,
    ) -> Vendor:
        vendor.compliance_score = score
        vendor.status = status
        vendor.risk_tier = risk_tier
        await self.db.flush()
        await self.db.refresh(vendor)
        return vendor
