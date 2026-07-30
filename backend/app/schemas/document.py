from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentType, DocumentStatus


class DocumentOut(BaseModel):
    id: str
    vendor_id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    document_type: DocumentType
    status: DocumentStatus
    # Phase 2 fields
    file_hash: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    document: DocumentOut
    message: str

