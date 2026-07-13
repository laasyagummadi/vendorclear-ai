# ─────────────────────────────────────────────────────────────
#  app/routes/documents.py  —  Document upload & listing
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.controllers.document_controller import DocumentController
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentOut, UploadResponse
from app.schemas.analysis import AnalysisOut

router = APIRouter(
    prefix="/vendors/{vendor_id}/documents",
    tags=["documents"],
)


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_document(
    vendor_id: str,
    file: UploadFile = File(...),
    doc_type_hint: str = Form(default="AUTO"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Upload a document (COI, Diversity Cert) and trigger AI analysis."""
    controller = DocumentController(db)
    analysis = await controller.upload_and_analyze(file, vendor_id, doc_type_hint)
    doc = await DocumentRepository.get_document(db, analysis.document_id)
    return UploadResponse(
        document=DocumentOut.model_validate(doc),
        message="Document uploaded and analysed successfully.",
    )


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
