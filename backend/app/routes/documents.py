# ─────────────────────────────────────────────────────────────
#  app/routes/documents.py  —  Document upload & listing
#  Phase 2 additions (Hruthi):
#   - Module 5: POST /bulk-upload — multiple files at once
#   - Module 7: POST /duplicate-check — pre-upload hash check
#   - Module 2: classification info exposed in upload response
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.utils.rbac import require_roles
from app.models.user import User, UserRole
from app.controllers.document_controller import DocumentController
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentOut, UploadResponse
from app.schemas.analysis import AnalysisOut
from app.utils.rate_limit import limiter
from app.services.ocr_service import compute_bytes_hash

router = APIRouter(
    prefix="/vendors/{vendor_id}/documents",
    tags=["documents"],
)


@router.post("", response_model=UploadResponse, status_code=201)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    vendor_id: str,
    file: UploadFile = File(...),
    doc_type_hint: str = Form(default="AUTO"),
    force: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.VENDOR)
    ),
):
    """Upload a document (COI, Diversity Cert) and trigger AI analysis."""
    controller = DocumentController(db)
    
    if not force:
        file_bytes = await file.read()
        await file.seek(0)
        file_hash = compute_bytes_hash(file_bytes)
        dup = await controller.check_duplicate(vendor_id, file_hash)
        if dup:
            raise HTTPException(
                status_code=409, 
                detail=f"Duplicate of '{dup['existing_filename']}' uploaded on {dup['uploaded_at'][:10]}"
            )

    analysis = await controller.upload_and_analyze(file, vendor_id, doc_type_hint)
    doc = await DocumentRepository.get_document(db, analysis.document_id)
    return UploadResponse(
        document=DocumentOut.model_validate(doc),
        message="Document uploaded and analysed successfully.",
    )


@router.post("/bulk-upload", status_code=202)
@limiter.limit("5/minute")
async def bulk_upload_documents(
    request: Request,
    vendor_id: str,
    files: List[UploadFile] = File(...),
    doc_type_hint: str = Form(default="AUTO"),
    force: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.VENDOR)
    ),
):
    """
    Module 5: Bulk upload multiple documents for a vendor.
    Each file is processed sequentially. Returns per-file results including
    status, analysis ID, and any errors encountered.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per bulk upload.")

    results = []
    controller = DocumentController(db)

    for file in files:
        file_result = {
            "filename": file.filename,
            "status": "processing",
            "document_id": None,
            "analysis_id": None,
            "document_type": None,
            "compliance_status": None,
            "duplicate": False,
            "error": None,
        }

        try:
            # Read bytes for hash check before upload
            file_bytes = await file.read()
            await file.seek(0)
            file_hash = compute_bytes_hash(file_bytes)

            # Check for duplicate
            if not force:
                dup = await controller.check_duplicate(vendor_id, file_hash)
                if dup:
                    file_result["status"] = "duplicate"
                    file_result["duplicate"] = True
                    file_result["document_id"] = dup["existing_document_id"]
                    file_result["error"] = (
                        f"Duplicate of '{dup['existing_filename']}' "
                        f"uploaded on {dup['uploaded_at'][:10]}"
                    )
                    results.append(file_result)
                    continue

            analysis = await controller.upload_and_analyze(file, vendor_id, doc_type_hint)
            doc = await DocumentRepository.get_document(db, analysis.document_id)

            file_result["status"] = "completed"
            file_result["document_id"] = doc.id if doc else None
            file_result["analysis_id"] = analysis.id
            file_result["document_type"] = doc.document_type.value if doc else None
            file_result["compliance_status"] = analysis.status.value

        except HTTPException as e:
            file_result["status"] = "failed"
            file_result["error"] = e.detail
        except Exception as e:
            file_result["status"] = "failed"
            file_result["error"] = str(e)

        results.append(file_result)

    total = len(results)
    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")
    duplicates = sum(1 for r in results if r["status"] == "duplicate")

    return {
        "summary": {
            "total": total,
            "completed": completed,
            "failed": failed,
            "duplicates": duplicates,
        },
        "results": results,
    }


@router.post("/duplicate-check", status_code=200)
async def check_duplicate_document(
    request: Request,
    vendor_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """
    Module 7: Pre-upload duplicate check. Reads the file, computes its
    SHA-256 hash, and checks if this vendor already has this exact document.
    Does NOT store anything. Returns { duplicate: bool, ... }.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty.")

    file_hash = compute_bytes_hash(file_bytes)
    controller = DocumentController(db)
    dup = await controller.check_duplicate(vendor_id, file_hash)

    if dup:
        return {"duplicate": True, **dup}
    return {"duplicate": False, "hash": file_hash}


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Return all documents for a vendor."""
    docs = await DocumentRepository.get_vendor_documents(db, vendor_id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    vendor_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Return a single document."""
    doc = await DocumentRepository.get_document(db, document_id)
    if not doc or doc.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/analyses", response_model=list[AnalysisOut])
async def list_document_analyses(
    vendor_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Return all analyses for a document."""
    doc = await DocumentRepository.get_document(db, document_id)
    if not doc or doc.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    analyses = await DocumentRepository.get_analyses_for_document(db, document_id)
    return [AnalysisOut.model_validate(a) for a in analyses]
