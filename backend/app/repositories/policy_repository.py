# ─────────────────────────────────────────────────────────────
#  app/repositories/policy_repository.py  —  CompliancePolicy DB ops
# ─────────────────────────────────────────────────────────────
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import CompliancePolicy
from app.models.vendor import VendorCategory
from app.schemas.policy import CompliancePolicyCreate, CompliancePolicyUpdate


class PolicyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        result = await self.db.execute(
            select(CompliancePolicy).where(CompliancePolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def get_by_category(self, category: VendorCategory) -> Optional[CompliancePolicy]:
        result = await self.db.execute(
            select(CompliancePolicy).where(CompliancePolicy.category == category)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[CompliancePolicy]:
        result = await self.db.execute(
            select(CompliancePolicy).order_by(CompliancePolicy.category)
        )
        return list(result.scalars().all())

    async def create(self, data: CompliancePolicyCreate) -> CompliancePolicy:
        policy = CompliancePolicy(**data.model_dump())
        self.db.add(policy)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def update(self, policy: CompliancePolicy, data: CompliancePolicyUpdate) -> CompliancePolicy:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(policy, field, value)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def delete(self, policy: CompliancePolicy) -> None:
        await self.db.delete(policy)
        await self.db.flush()

    async def seed_defaults_if_missing(self) -> List[CompliancePolicy]:
        """Create a default policy for every VendorCategory that doesn't
        already have one configured. Called once at startup so the
        category dropdown always has real, editable policies behind it
        instead of silently falling back to defaults forever."""
        existing = {p.category for p in await self.get_all()}
        created = []
        defaults = {
            VendorCategory.CONSTRUCTION: dict(
                name="Construction (default)",
                description="Heavier weight on insurance validity — field crews carry more liability exposure.",
                weight_status=0.30, weight_documents=0.25, weight_expiry=0.35, weight_diversity=0.10,
                finding_penalty_critical=12.0, finding_penalty_high=6.0, finding_penalty_medium=3.0,
                required_document_types=["COI", "DIVERSITY_CERT"],
                risk_low_min_score=80.0, risk_medium_min_score=55.0,
            ),
            VendorCategory.SOFTWARE: dict(
                name="Software (default)",
                description="Lighter insurance weighting, heavier status/documentation — physical COI/WC less central for SaaS vendors.",
                weight_status=0.45, weight_documents=0.35, weight_expiry=0.10, weight_diversity=0.10,
                finding_penalty_critical=10.0, finding_penalty_high=5.0, finding_penalty_medium=2.0,
                required_document_types=["COI"],
                risk_low_min_score=75.0, risk_medium_min_score=50.0,
            ),
            VendorCategory.ELECTRICAL: dict(
                name="Electrical (default)",
                description="Highest-risk category — strict expiry and status weighting, steep penalties for critical findings.",
                weight_status=0.35, weight_documents=0.20, weight_expiry=0.35, weight_diversity=0.10,
                finding_penalty_critical=15.0, finding_penalty_high=8.0, finding_penalty_medium=4.0,
                required_document_types=["COI", "DIVERSITY_CERT"],
                risk_low_min_score=85.0, risk_medium_min_score=60.0,
            ),
            VendorCategory.TRANSPORTATION: dict(
                name="Transportation (default)",
                description="Fleet/hauling vendors — auto liability and expiry are the dominant risk signals, so coverage validity is weighted heavily alongside status.",
                weight_status=0.35, weight_documents=0.20, weight_expiry=0.35, weight_diversity=0.10,
                finding_penalty_critical=13.0, finding_penalty_high=7.0, finding_penalty_medium=3.0,
                required_document_types=["COI"],
                risk_low_min_score=80.0, risk_medium_min_score=55.0,
            ),
            VendorCategory.CIVIL: dict(
                name="Civil Contractors (default)",
                description="Civil contractors carry similar field-crew liability exposure to Construction — expiry and documentation are weighted evenly with status.",
                weight_status=0.30, weight_documents=0.25, weight_expiry=0.30, weight_diversity=0.15,
                finding_penalty_critical=12.0, finding_penalty_high=6.0, finding_penalty_medium=3.0,
                required_document_types=["COI", "DIVERSITY_CERT"],
                risk_low_min_score=80.0, risk_medium_min_score=55.0,
            ),
            VendorCategory.OTHER: dict(
                name="General (default)",
                description="Baseline policy for vendors that don't fall into a specialized category.",
                weight_status=0.40, weight_documents=0.30, weight_expiry=0.20, weight_diversity=0.10,
                finding_penalty_critical=10.0, finding_penalty_high=5.0, finding_penalty_medium=2.0,
                required_document_types=["COI", "DIVERSITY_CERT"],
                risk_low_min_score=75.0, risk_medium_min_score=50.0,
            ),
        }
        for category, fields in defaults.items():
            if category in existing:
                continue
            policy = CompliancePolicy(category=category, is_active=True, **fields)
            self.db.add(policy)
            created.append(policy)
        if created:
            await self.db.flush()
        return created
