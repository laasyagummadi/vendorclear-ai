# ─────────────────────────────────────────────────────────────
#  app/controllers/policy_controller.py  —  CompliancePolicy business logic
# ─────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import (
    CompliancePolicyCreate, CompliancePolicyUpdate, CompliancePolicyResponse,
)
from app.models.vendor import VendorCategory
from app.utils.exceptions import NotFoundError, ConflictError


class PolicyController:
    def __init__(self, db: AsyncSession):
        self.repo = PolicyRepository(db)

    async def list_policies(self) -> list[CompliancePolicyResponse]:
        await self.repo.seed_defaults_if_missing()
        policies = await self.repo.get_all()
        return [CompliancePolicyResponse.model_validate(p) for p in policies]

    async def get_policy(self, policy_id: str) -> CompliancePolicyResponse:
        policy = await self.repo.get_by_id(policy_id)
        if not policy:
            raise NotFoundError("Compliance policy")
        return CompliancePolicyResponse.model_validate(policy)

    async def create_policy(self, data: CompliancePolicyCreate) -> CompliancePolicyResponse:
        existing = await self.repo.get_by_category(data.category)
        if existing:
            raise ConflictError(f"A policy for category {data.category.value} already exists")
        policy = await self.repo.create(data)
        logger.info(f"Compliance policy created: {policy.category} (id={policy.id})")
        return CompliancePolicyResponse.model_validate(policy)

    async def update_policy(self, policy_id: str, data: CompliancePolicyUpdate) -> CompliancePolicyResponse:
        policy = await self.repo.get_by_id(policy_id)
        if not policy:
            raise NotFoundError("Compliance policy")
        policy = await self.repo.update(policy, data)
        logger.info(f"Compliance policy updated: {policy.category} (id={policy.id})")
        return CompliancePolicyResponse.model_validate(policy)

    async def delete_policy(self, policy_id: str) -> dict:
        policy = await self.repo.get_by_id(policy_id)
        if not policy:
            raise NotFoundError("Compliance policy")
        category = policy.category.value
        await self.repo.delete(policy)
        logger.info(f"Compliance policy deleted: {category}")
        return {"message": f"Policy for {category} deleted — vendors in that category will use the bootstrap default until a new one is created."}
