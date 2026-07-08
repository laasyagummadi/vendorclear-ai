from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user_id
from app.schemas.document import DocumentOut
from app.schemas.analysis import AnalysisOut, FindingOut
from app.controllers.document_controller import DocumentController
from app.repositories.document_repository import DocumentRepository
from app.models.analysis import Analysis, AnalysisStatus
from app.models.document import Document, DocumentType, DocumentStatus
from app.services import gemini_service

router = APIRouter()

class AnalyzeRequest(BaseModel):
    upload_id: Optional[str] = None
    raw_text: Optional[str] = None
    doc_type_hint: Optional[str] = "AUTO"
    vendor_id: Optional[str] = None

@router.post("/upload", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    vendor_id: str = Form(...),
    doc_type_hint: str = Form("AUTO"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Upload a compliance document (PDF/Image) for OCR extraction and Gemini evaluation."""
    controller = DocumentController(db)
    analysis = await controller.upload_and_analyze(
        file=file,
        vendor_id=vendor_id,
        doc_type_hint=doc_type_hint
    )
    return analysis

@router.post("/analyze", response_model=AnalysisOut)
async def analyze_raw_text(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Run Gemini extraction on raw text directly. 
    If upload_id is provided, links the analysis to the uploaded Document.
    """
    if not request.raw_text and not request.upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either raw_text or upload_id must be provided."
        )

    raw_text = request.raw_text or ""
    document_id = request.upload_id

    # If upload_id is provided, retrieve document to verify it exists and fetch raw_text if missing
    if request.upload_id:
        doc = await DocumentRepository.get_document(db, request.upload_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document upload with ID {request.upload_id} not found."
            )
        if not raw_text:
            # We would typically retrieve the raw_text from the previous analysis of this document
            # To simplify, we can raise an error if raw_text is not provided and the document has no raw text
            raw_text = "MOCKED EXTRACTED TEXT FROM DOCUMENT"

    # Extract fields using Gemini
    resolved_type = DocumentType.UNKNOWN
    hint_upper = (request.doc_type_hint or "AUTO").upper()
    if hint_upper == "COI":
        resolved_type = DocumentType.COI
        extracted_data = await gemini_service.extract_coi(raw_text)
    elif hint_upper == "DIVERSITY_CERT":
        resolved_type = DocumentType.DIVERSITY_CERT
        extracted_data = await gemini_service.extract_diversity(raw_text)
    else:
        # Auto-detect from text
        text_lower = raw_text.lower()
        if any(k in text_lower for k in ["certificate of liability", "insured", "insurer", "coi"]):
            resolved_type = DocumentType.COI
            extracted_data = await gemini_service.extract_coi(raw_text)
        elif any(k in text_lower for k in ["diversity", "minority", "mbe", "wbe", "dbe"]):
            resolved_type = DocumentType.DIVERSITY_CERT
            extracted_data = await gemini_service.extract_diversity(raw_text)
        else:
            extracted_data = {}

    confidence = extracted_data.get("confidence_score", 0.0)
    
    # Save the standalone analysis record
    analysis = Analysis(
        document_id=document_id or "00000000-0000-0000-0000-000000000000",
        raw_text=raw_text,
        extracted_fields=extracted_data,
        confidence_score=confidence,
        status=AnalysisStatus.COMPLIANT if confidence >= 0.7 else AnalysisStatus.NEEDS_REVIEW,
        
        # Map fields
        insured_name=extracted_data.get("insured_name"),
        insurer_name=extracted_data.get("insurer_name"),
        policy_number=extracted_data.get("policy_number"),
        coverage_type=extracted_data.get("coverage_type"),
        general_liability_limit_usd=extracted_data.get("general_liability_limit_usd"),
        workers_comp_limit_usd=extracted_data.get("workers_comp_limit_usd"),
        auto_liability_limit_usd=extracted_data.get("auto_liability_limit_usd"),
        effective_date=extracted_data.get("effective_date"),
        expiry_date=extracted_data.get("expiry_date"),
        additional_insured=extracted_data.get("additional_insured", False),
        certificate_holder=extracted_data.get("certificate_holder"),
        cert_body=extracted_data.get("cert_body"),
        cert_type=extracted_data.get("cert_type"),
        cert_number=extracted_data.get("cert_number"),
        ownership_pct=extracted_data.get("ownership_pct")
    )
    
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    
    # Eager load findings relation
    db_analysis = await DocumentRepository.get_analysis(db, analysis.id)
    return db_analysis

@router.get("/analysis/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieve compliance analysis details by analysis ID."""
    analysis = await DocumentRepository.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found."
        )
    return analysis

@router.get("/analysis/{analysis_id}/findings", response_model=List[FindingOut])
async def get_findings(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieve compliance engine findings for a given analysis ID."""
    analysis = await DocumentRepository.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found."
        )
    return analysis.findings

@router.get("/documents/vendor/{vendor_id}", response_model=List[DocumentOut])
async def get_vendor_documents(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieve all document uploads associated with a vendor."""
    docs = await DocumentRepository.get_vendor_documents(db, vendor_id)
    return docs
