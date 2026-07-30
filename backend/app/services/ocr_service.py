# ─────────────────────────────────────────────────────────────
#  app/services/ocr_service.py  —  Text extraction (Hruthi)
#  Phase 2 upgrades:
#   - Graceful error handling for corrupted / password-protected PDFs
#   - Per-page OCR fallback with rotation correction for blurry scans
#   - Multi-page PDF support with page-level error recovery
#   - SHA-256 file hash helper for duplicate detection (Module 7)
#   - Blank-document detection (returns empty string + warning)
# ─────────────────────────────────────────────────────────────
import hashlib
import io
import os
from loguru import logger

try:
    import pdfplumber
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
    logger.warning("pdfplumber not installed — PDF text extraction disabled")

try:
    from PIL import Image
    import pytesseract
    # On Windows, point to the Tesseract executable
    if os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    logger.warning("pytesseract / Pillow not installed — image OCR disabled")

try:
    import docx as _docx
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False
    logger.warning("python-docx not installed — DOCX text extraction disabled")


# ── Duplicate detection helper ────────────────────────────────

def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file for duplicate detection."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_bytes_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw bytes (for pre-save duplicate check)."""
    return hashlib.sha256(data).hexdigest()


# ── PDF helpers ───────────────────────────────────────────────

def _is_password_protected(file_path: str) -> bool:
    """Return True if the PDF requires a password to open."""
    if not _PDF_AVAILABLE:
        return False
    try:
        with pdfplumber.open(file_path) as pdf:
            _ = pdf.pages  # triggers decryption check
        return False
    except Exception as e:
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            return True
        return False


def _ocr_image(img: "Image.Image") -> str:
    """Run Tesseract on a PIL Image, trying multiple rotations if blank."""
    if not _OCR_AVAILABLE:
        return ""
    text = pytesseract.image_to_string(img)
    if len(text.strip()) < 20:
        # Try 90° rotations for upside-down / rotated scans
        for angle in [90, 180, 270]:
            rotated = img.rotate(angle, expand=True)
            candidate = pytesseract.image_to_string(rotated)
            if len(candidate.strip()) > len(text.strip()):
                text = candidate
    return text


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF.

    Strategy:
    1. Try native pdfplumber text layer (fastest, most accurate).
    2. If the native layer yields nothing (scanned PDF), fall back to
       per-page image OCR with rotation correction.
    3. Raise meaningful exceptions for encrypted / corrupt files.
    """
    if not _PDF_AVAILABLE:
        return ""

    if _is_password_protected(file_path):
        raise ValueError(
            "PDF is password-protected. Please provide an unlocked version."
        )

    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF has no pages — the file may be blank or corrupt.")

            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Page {i+1} native extraction failed: {e}")
                    text_parts.append("")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not open PDF — the file may be corrupt: {e}")

    native_text = "\n".join(text_parts).strip()

    # If native text layer is empty or very sparse, switch to image OCR
    if len(native_text) < 30 and _OCR_AVAILABLE:
        logger.info(f"Sparse native text, switching to image OCR: {file_path}")
        ocr_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    try:
                        img = page.to_image(resolution=300).original
                        ocr_parts.append(_ocr_image(img))
                    except Exception as e:
                        logger.warning(f"OCR failed for page {i+1}: {e}")
                        ocr_parts.append("")
        except Exception as e:
            logger.error(f"Image OCR pass failed: {e}")
        return "\n".join(ocr_parts).strip()

    return native_text


def extract_text_from_image(file_path: str) -> str:
    """Extract text from an image using Tesseract OCR with rotation correction."""
    if not _OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(file_path)
        return _ocr_image(img)
    except Exception as e:
        raise ValueError(f"Could not read image file: {e}")


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a Word (.docx) document."""
    if not _DOCX_AVAILABLE:
        return ""
    try:
        document = _docx.Document(file_path)
        parts = [p.text for p in document.paragraphs if p.text]
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        parts.append(cell.text)
        return "\n".join(parts)
    except Exception as e:
        raise ValueError(f"Could not read DOCX file: {e}")


def extract_text(file_path: str) -> str:
    """
    Dispatch to the correct extractor based on file extension.
    Raises ValueError with a user-friendly message for unsupported or
    unreadable files.
    """
    if not os.path.exists(file_path):
        raise ValueError("Uploaded file not found on disk.")

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise ValueError("The uploaded file is empty (0 bytes).")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
        return extract_text_from_image(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            "Accepted formats: PDF, PNG, JPG, JPEG, TIFF, DOCX."
        )
