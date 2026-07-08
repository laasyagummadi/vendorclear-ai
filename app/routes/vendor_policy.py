from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.vendor_policy import (
    VendorPolicyCreate,
    VendorPolicyUpdate,
    VendorPolicyResponse,
)
from app.services.vendor_policy import VendorPolicyService

router = APIRouter(
    prefix="/vendor-policies",
    tags=["Vendor Policies"]
)


@router.post("/", response_model=VendorPolicyResponse)
def create_vendor_policy(
    policy: VendorPolicyCreate,
    db: Session = Depends(get_db)
):
    return VendorPolicyService.create_policy(db, policy)


@router.get("/", response_model=List[VendorPolicyResponse])
def get_all_vendor_policies(
    db: Session = Depends(get_db)
):
    return VendorPolicyService.get_all_policies(db)


@router.get("/{policy_id}", response_model=VendorPolicyResponse)
def get_vendor_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    return VendorPolicyService.get_policy_by_id(db, policy_id)


@router.put("/{policy_id}", response_model=VendorPolicyResponse)
def update_vendor_policy(
    policy_id: int,
    policy: VendorPolicyUpdate,
    db: Session = Depends(get_db)
):
    return VendorPolicyService.update_policy(
        db,
        policy_id,
        policy
    )


@router.delete("/{policy_id}")
def delete_vendor_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    return VendorPolicyService.delete_policy(
        db,
        policy_id
    )
