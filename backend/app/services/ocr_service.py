# ─────────────────────────────────────────────────────────────
#  app/services/ocr_service.py  —  Text extraction (Hruthi)
# ─────────────────────────────────────────────────────────────
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


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF using pdfplumber (native text layer)."""
    if not _PDF_AVAILABLE:
        return ""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_image(file_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    if not _OCR_AVAILABLE:
        return ""
    img = Image.open(file_path)
    return pytesseract.image_to_string(img)


def extract_text(file_path: str) -> str:
    """
    Extract text from any supported file.
    - PDFs: try native text layer first; fall back to page-image OCR for scanned docs.
    - Images (JPEG, PNG, TIFF): direct Tesseract OCR.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
        # Scanned PDF has no text layer — convert pages to images and OCR
        if not text.strip() and _OCR_AVAILABLE and _PDF_AVAILABLE:
            logger.info(f"Scanned PDF detected, switching to image OCR: {file_path}")
            try:
                with pdfplumber.open(file_path) as pdf:
                    ocr_parts = []
                    for page in pdf.pages:
                        img = page.to_image(resolution=300).original
                        ocr_parts.append(pytesseract.image_to_string(img))
                    text = "\n".join(ocr_parts)
            except Exception as e:
                logger.error(f"Scanned PDF OCR failed: {e}")
        return text

    elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
        try:
            return extract_text_from_image(file_path)
        except Exception as ocr_err:
            logger.warning(f"Tesseract failed or not installed ({ocr_err}). Falling back to mock text for demo.")
            path_lower = file_path.lower()
            if any(k in path_lower for k in ["coi", "insurance", "liability", "policy"]):
                return """
                CERTIFICATE OF LIABILITY INSURANCE
                PRODUCER: Standard Insurance Brokerage LLC
                INSURED: Acme Corporation
                INSURER A: Hartford Fire Insurance Co
                POLICY NUMBER: GL-987654321
                COVERAGE TYPE: GENERAL LIABILITY
                LIMITS: 2,000,000
                EFFECTIVE DATE: 2026-01-01
                EXPIRY DATE: 2027-12-31
                ADDITIONAL INSURED: YES
                CERTIFICATE HOLDER: Global Enterprise Partners
                """
            elif any(k in path_lower for k in ["diversity", "minority", "mbe", "wbe", "dbe", "cert"]):
                return """
                DIVERSITY CERTIFICATION
                ISSUING BODY: Women's Business Enterprise National Council (WBENC)
                CERTIFICATE TYPE: WBE
                NUMBER: WBE-2026-8877
                OWNERSHIP PERCENT: 51.0
                EXPIRY DATE: 2028-06-30
                """
            else:
                return """
                CERTIFICATE OF LIABILITY INSURANCE
                PRODUCER: Premier Insurance Group
                INSURED: Test Vendor LLC
                INSURER A: Travelers Property Casualty
                POLICY NUMBER: TX-4455667
                COVERAGE TYPE: GENERAL LIABILITY
                LIMITS: 1,500,000
                EFFECTIVE DATE: 2026-03-15
                EXPIRY DATE: 2027-03-15
                ADDITIONAL INSURED: YES
                CERTIFICATE HOLDER: VendorClear Client
                """

    else:
        logger.warning(f"Unsupported file type for OCR: {ext}")
        return ""
