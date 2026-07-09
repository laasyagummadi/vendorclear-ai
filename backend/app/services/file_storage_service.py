# ─────────────────────────────────────────────────────────────
#  app/services/file_storage_service.py  —  Async file upload (Hruthi)
# ─────────────────────────────────────────────────────────────
import os
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
import aiofiles

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
CHUNK_SIZE = 64 * 1024  # 64 KB


async def save_upload(file: UploadFile) -> tuple[str, int]:
    """Validate and save an uploaded file; returns (file_path, file_size_bytes)."""

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, JPEG, PNG, TIFF, DOCX.",
        )

    # Build upload directory: ./uploads/YYYY/MM/
    now = datetime.utcnow()
    upload_dir = os.path.join("uploads", str(now.year), f"{now.month:02d}")
    os.makedirs(upload_dir, exist_ok=True)

    # Unique filename to avoid collisions
    timestamp = now.strftime("%Y%m%d%H%M%S%f")
    safe_name = file.filename.replace(" ", "_")
    dest_path = os.path.join(upload_dir, f"{timestamp}_{safe_name}")

    total_bytes = 0
    async with aiofiles.open(dest_path, "wb") as out_file:
        while chunk := await file.read(CHUNK_SIZE):
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_BYTES:
                await out_file.close()
                os.remove(dest_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the 20 MB size limit.",
                )
            await out_file.write(chunk)

    return dest_path, total_bytes
