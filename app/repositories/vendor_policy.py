from sqlalchemy.orm import Session

from app.models.vendor_policy import VendorPolicy
from app.schemas.vendor_policy import (
    VendorPolicyCreate,
    VendorPolicyUpdate,
)


class VendorPolicyRepository:

    @staticmethod
    def create(db: Session, policy: VendorPolicyCreate):
        db_policy = VendorPolicy(**policy.model_dump())
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        return db_policy

    @staticmethod
    def get_all(db: Session):
        return db.query(VendorPolicy).all()

    @staticmethod
    def get_by_id(db: Session, policy_id: int):
        return db.query(VendorPolicy).filter(
            VendorPolicy.id == policy_id
        ).first()

    @staticmethod
    def update(
        db: Session,
        db_policy: VendorPolicy,
        policy: VendorPolicyUpdate,
    ):
        update_data = policy.model_dump()

        for key, value in update_data.items():
            setattr(db_policy, key, value)

        db.commit()
        db.refresh(db_policy)
        return db_policy

    @staticmethod
    def delete(db: Session, db_policy: VendorPolicy):
        db.delete(db_policy)
        db.commit()
