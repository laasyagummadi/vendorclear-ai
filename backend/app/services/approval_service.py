# ─────────────────────────────────────────────────────────────
#  app/services/approval_service.py  —  Module 9 approval workflow
# ─────────────────────────────────────────────────────────────
from datetime import datetime, date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import ApprovalPolicy, ApprovalSubmission, SubmissionStatus
from app.models.vendor import Vendor, VendorStatus
from app.models.analysis import Analysis
from app.models.document import Document


# Which transitions are legal. Anything not listed is rejected, so a
# submission can never jump from e.g. REJECTED straight to ACTIVE.
ALLOWED_TRANSITIONS: dict[SubmissionStatus, set[SubmissionStatus]] = {
    SubmissionStatus.DRAFT:    {SubmissionStatus.PENDING},
    SubmissionStatus.PENDING:  {SubmissionStatus.APPROVED, SubmissionStatus.REJECTED},
    SubmissionStatus.APPROVED: {SubmissionStatus.ACTIVE, SubmissionStatus.REJECTED},
    SubmissionStatus.REJECTED: {SubmissionStatus.PENDING},   # resubmission
    SubmissionStatus.ACTIVE:   {SubmissionStatus.EXPIRED, SubmissionStatus.REJECTED},
    SubmissionStatus.EXPIRED:  {SubmissionStatus.PENDING},
}


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Policies ──────────────────────────────────────────────
    async def create_policy(self, data: dict, created_by_id: Optional[str]) -> ApprovalPolicy:
        policy = ApprovalPolicy(
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            version=data.get("version", 1),
            requirements=data.get("requirements", {}),
            created_by_id=created_by_id,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def list_policies(self, version: Optional[int] = None, active_only: bool = True):
        stmt = select(ApprovalPolicy)
        if version is not None:
            stmt = stmt.where(ApprovalPolicy.version == version)
        if active_only:
            stmt = stmt.where(ApprovalPolicy.is_active == True)  # noqa: E712
        stmt = stmt.order_by(ApprovalPolicy.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_policy(self, policy_id: str) -> Optional[ApprovalPolicy]:
        return await self.db.get(ApprovalPolicy, policy_id)

    async def update_policy(self, policy: ApprovalPolicy, updates: dict) -> ApprovalPolicy:
        for field in ("name", "description", "category", "version", "requirements", "is_active"):
            if field in updates and updates[field] is not None:
                setattr(policy, field, updates[field])
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    # ── Requirement checking ──────────────────────────────────
    async def check_requirements(self, vendor_id: str, policy: ApprovalPolicy) -> tuple[bool, dict]:
        """
        Evaluate a vendor's analysed documents against a policy's requirements.
        Returns (meets_all, per-requirement results) so a reviewer can see
        exactly which items passed or failed.
        """
        req = policy.requirements or {}
        results: dict = {}

        # Pull the vendor's analyses (via their documents)
        analyses = list((await self.db.execute(
            select(Analysis).join(Document, Analysis.document_id == Document.id)
            .where(Document.vendor_id == vendor_id)
        )).scalars().all())

        best_gl = max((a.general_liability_limit_usd or 0) for a in analyses) if analyses else 0
        has_wc = any((a.workers_comp_limit_usd or 0) > 0 for a in analyses)
        # umbrella/excess is captured in coverage_type text when present
        has_umbrella = any(
            "umbrella" in (a.coverage_type or "").lower() or "excess" in (a.coverage_type or "").lower()
            for a in analyses
        )
        latest_expiry = None
        for a in analyses:
            if a.expiry_date and (latest_expiry is None or a.expiry_date > latest_expiry):
                latest_expiry = a.expiry_date

        if "required_gl_limit_usd" in req:
            needed = req["required_gl_limit_usd"] or 0
            results["general_liability"] = {
                "required": needed, "found": best_gl, "passed": best_gl >= needed,
            }
        if req.get("workers_comp_required"):
            results["workers_comp"] = {
                "required": True, "found": has_wc, "passed": has_wc,
            }
        if req.get("umbrella_required"):
            results["umbrella"] = {
                "required": True, "found": has_umbrella, "passed": has_umbrella,
            }
        if req.get("must_not_be_expired"):
            ok = bool(latest_expiry) and str(latest_expiry) >= date.today().isoformat()
            results["not_expired"] = {
                "required": True, "found": str(latest_expiry) if latest_expiry else None, "passed": ok,
            }
        if not analyses:
            results["documents"] = {
                "required": True, "found": 0,
                "passed": False, "note": "No analysed documents on file for this vendor.",
            }

        meets = bool(results) and all(r.get("passed") for r in results.values())
        return meets, results

    # ── Submissions ───────────────────────────────────────────
    async def create_submission(
        self, vendor_id: str, policy_id: str,
        submitted_by_id: Optional[str], document_ids: Optional[list] = None,
    ) -> ApprovalSubmission:
        policy = await self.get_policy(policy_id)
        if not policy:
            raise ValueError("Policy not found.")
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            raise ValueError("Vendor not found.")

        meets, results = await self.check_requirements(vendor_id, policy)

        submission = ApprovalSubmission(
            policy_id=policy_id,
            vendor_id=vendor_id,
            status=SubmissionStatus.PENDING,
            document_ids=document_ids or [],
            requirement_results=results,
            meets_requirements=meets,
            submitted_by_id=submitted_by_id,
            submitted_at=datetime.utcnow().isoformat(),
        )
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def list_submissions(
        self, status: Optional[SubmissionStatus] = None,
        vendor_id: Optional[str] = None,
    ):
        stmt = select(ApprovalSubmission)
        if status:
            stmt = stmt.where(ApprovalSubmission.status == status)
        if vendor_id:
            stmt = stmt.where(ApprovalSubmission.vendor_id == vendor_id)
        stmt = stmt.order_by(ApprovalSubmission.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_submission(self, submission_id: str) -> Optional[ApprovalSubmission]:
        return await self.db.get(ApprovalSubmission, submission_id)

    async def transition(
        self, submission: ApprovalSubmission, new_status: SubmissionStatus,
        reviewer_id: Optional[str] = None, notes: Optional[str] = None,
    ) -> ApprovalSubmission:
        """Move a submission to a new status, enforcing the state machine."""
        current = submission.status
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Cannot move a submission from {current.value} to {new_status.value}."
            )

        submission.status = new_status
        if new_status in (SubmissionStatus.APPROVED, SubmissionStatus.REJECTED):
            submission.reviewed_by_id = reviewer_id
            submission.reviewed_at = datetime.utcnow().isoformat()
            if notes:
                submission.review_notes = notes
        self.db.add(submission)

        # Approval activates the submission and marks the vendor compliant.
        if new_status == SubmissionStatus.APPROVED:
            submission.status = SubmissionStatus.ACTIVE
            vendor = await self.db.get(Vendor, submission.vendor_id)
            if vendor:
                vendor.status = VendorStatus.COMPLIANT
                self.db.add(vendor)

        # M7 audit trail: record every approval decision.
        from app.services.audit_service import AuditService
        from app.models.audit import AuditAction
        action_map = {
            SubmissionStatus.APPROVED: AuditAction.APPROVE,
            SubmissionStatus.REJECTED: AuditAction.REJECT,
        }
        if new_status in action_map:
            from app.models.user import User
            reviewer = await self.db.get(User, reviewer_id) if reviewer_id else None
            await AuditService(self.db).log(
                action_map[new_status], "policy_submission",
                entity_id=submission.id,
                entity_name=f"Submission for vendor {submission.vendor_id}",
                actor=reviewer,
                changes={"status": {"from": current.value, "to": submission.status.value}},
                summary=notes or f"Submission {new_status.value.lower()}",
                commit=False,
            )

        await self.db.commit()
        await self.db.refresh(submission)
        return submission
