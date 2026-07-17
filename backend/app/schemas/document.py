from datetime import datetime
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    document: DocumentOut
    message: str
