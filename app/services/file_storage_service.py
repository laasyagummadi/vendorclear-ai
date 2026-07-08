import os
import aiofiles
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from loguru import logger

# ── Config defaults ───────────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

def validate_file(file: UploadFile):
    """Validate MIME type."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Rejected upload: unsupported MIME type {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed types are PDF, JPEG, PNG, TIFF, and DOCX."
        )

async def save_upload(file: UploadFile) -> tuple[str, int]:
    """
    Save the upload file asynchronously under {UPLOAD_DIR}/{YYYY}/{MM}/filename.
    Returns: (file_path, file_size_bytes)
    """
    validate_file(file)
    
    # 1. Setup target directory path
    now = datetime.utcnow()
    sub_path = os.path.join(str(now.year), f"{now.month:02d}")
    target_dir = os.path.join(UPLOAD_DIR, sub_path)
    os.makedirs(target_dir, exist_ok=True)

    # 2. Prevent directory traversal
    safe_filename = os.path.basename(file.filename)
    # Deduplicate filename if it already exists
    base, ext = os.path.splitext(safe_filename)
    file_path = os.path.join(target_dir, safe_filename)
    counter = 1
    while os.path.exists(file_path):
        safe_filename = f"{base}_{counter}{ext}"
        file_path = os.path.join(target_dir, safe_filename)
        counter += 1

    # 3. Read and write file in chunks to validate size
    size_limit = MAX_FILE_SIZE_MB * 1024 * 1024
    total_bytes = 0
    
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > size_limit:
                    logger.warning(f"Rejected upload: file size exceeds {MAX_FILE_SIZE_MB}MB limit")
                    # Delete the partial file
                    out_file.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB."
                    )
                await out_file.write(chunk)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error saving uploaded file: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while saving file on server."
        )

    logger.info(f"File saved successfully: {file_path} ({total_bytes} bytes)")
    return file_path, total_bytes
