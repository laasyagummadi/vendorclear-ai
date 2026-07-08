import os
import pdfplumber
from PIL import Image
import pytesseract
from loguru import logger

TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
else:
    logger.warning(f"Tesseract executable not found at specified path: {TESSERACT_CMD}. Image OCR may fail if tesseract is not on the system PATH.")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text using pdfplumber."""
    text_content = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
    return "\n".join(text_content)

def extract_text_from_image(file_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    with Image.open(file_path) as img:
        return pytesseract.image_to_string(img)

def extract_text(file_path: str) -> str:
    """
    Main text extraction coordinator.
    Handles native text PDFs, scanned PDFs (via character count check), and images.
    Returns combined text, or empty string on failure.
    """
    path_lower = file_path.lower()
    combined_text = ""
    
    try:
        if path_lower.endswith(".pdf"):
            logger.info(f"Extracting native text from PDF: {file_path}")
            combined_text = extract_text_from_pdf(file_path)
            
            # Scanned PDF check: if extracted text is very short, fallback to OCR
            if len(combined_text.strip()) < 100:
                logger.info(f"PDF text length ({len(combined_text)}) is low. Retrying with Tesseract OCR.")
                # We extract text from each page converted to image
                # In standard environments, pdfplumber/pdf2image can be used. We will do a page-by-page tesseract fallback or log warning.
                # Since pytesseract requires image files, we can extract images from pdfplumber or warn.
                # Let's try to extract text from images in the PDF using pdfplumber's image objects if possible, or log a warning.
                # To keep it robust and simple:
                ocr_text = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        # Convert page to image object
                        pil_image = page.to_image(resolution=150).original
                        page_ocr = pytesseract.image_to_string(pil_image)
                        if page_ocr:
                            ocr_text.append(page_ocr)
                combined_text = "\n".join(ocr_text)
                
        elif path_lower.endswith((".jpg", ".jpeg", ".png", ".tiff")):
            logger.info(f"Extracting text from image: {file_path}")
            combined_text = extract_text_from_image(file_path)
        else:
            logger.warning(f"Unsupported file format for text extraction: {file_path}")
            combined_text = ""
            
    except Exception as e:
        logger.error(f"Error during text extraction from {file_path}: {str(e)}")
        # Safe fallback: do not crash the pipeline, return whatever we have or empty string
        combined_text = ""

    return combined_text
