from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repository.vendor_policy import VendorPolicyRepository
from app.schemas.vendor_policy import (
    VendorPolicyCreate,
    VendorPolicyUpdate,
)


class VendorPolicyService:

    @staticmethod
    def create_policy(db: Session, policy: VendorPolicyCreate):
        return VendorPolicyRepository.create(db, policy)

    @staticmethod
    def get_all_policies(db: Session):
        return VendorPolicyRepository.get_all(db)

    @staticmethod
    def get_policy_by_id(db: Session, policy_id: int):
        policy = VendorPolicyRepository.get_by_id(db, policy_id)

        if not policy:
            raise HTTPException(
                status_code=404,
                detail="Vendor Policy not found"
            )

        return policy

    @staticmethod
    def update_policy(
        db: Session,
        policy_id: int,
        policy: VendorPolicyUpdate
    ):
        db_policy = VendorPolicyRepository.get_by_id(
            db,
            policy_id
        )

        if not db_policy:
            raise HTTPException(
                status_code=404,
                detail="Vendor Policy not found"
            )

        return VendorPolicyRepository.update(
            db,
            db_policy,
            policy
        )

    @staticmethod
    def delete_policy(db: Session, policy_id: int):

        db_policy = VendorPolicyRepository.get_by_id(
            db,
            policy_id
        )

        if not db_policy:
            raise HTTPException(
                status_code=404,
                detail="Vendor Policy not found"
            )

        VendorPolicyRepository.delete(db, db_policy)

        return {
            "message": "Vendor Policy deleted successfully"
        }
