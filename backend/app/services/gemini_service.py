# ─────────────────────────────────────────────────────────────
#  app/services/gemini_service.py  —  Gemini AI extraction (Hruthi)
# ─────────────────────────────────────────────────────────────
import json
import re
from loguru import logger

try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed — using mock extraction")

from config import settings

# Initialise Gemini once on import (skipped when key is absent)
_model = None
if _GEMINI_AVAILABLE and settings.gemini_api_key:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            "gemini-2.0-flash-lite",
            generation_config={"response_mime_type": "application/json"},
        )
        logger.info("Gemini 2.0 Flash-Lite model initialized")
    except Exception as e:
        logger.warning(f"Gemini init failed, using mock: {e}")


# ── COI extraction ────────────────────────────────────────────

COI_PROMPT = """
Extract the following fields from this Certificate of Insurance (COI) text and return ONLY a JSON object:
{
  "insured_name": string or null,
  "insurer_name": string or null,
  "policy_number": string or null,
  "coverage_type": string or null,
  "general_liability_limit_usd": number or null,
  "workers_comp_limit_usd": number or null,
  "auto_liability_limit_usd": number or null,
  "effective_date": "YYYY-MM-DD" or null,
  "expiry_date": "YYYY-MM-DD" or null,
  "additional_insured": boolean or null,
  "certificate_holder": string or null,
  "confidence_score": number between 0.0 and 1.0
}

COI Text:
"""

DIVERSITY_PROMPT = """
Extract the following fields from this Diversity/Minority Business Certificate text and return ONLY a JSON object:
{
  "cert_body": string or null,
  "cert_type": string or null (e.g. "MBE", "WBE", "DBE", "SBE"),
  "cert_number": string or null,
  "ownership_pct": number or null (percentage 0-100),
  "expiry_date": "YYYY-MM-DD" or null,
  "confidence_score": number between 0.0 and 1.0
}

Certificate Text:
"""


# Fallback list of free models to try if quota is exceeded
FALLBACK_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

async def _call_gemini_with_fallback(prompt: str, raw_text: str) -> dict:
    """Tries multiple Gemini models sequentially to bypass free tier rate limits."""
    if not _GEMINI_AVAILABLE or not settings.gemini_api_key or not raw_text.strip():
        raise ValueError("No API key or empty text")

    last_err = None
    for model_name in FALLBACK_MODELS:
        try:
            logger.info(f"Attempting extraction with {model_name}...")
            model = genai.GenerativeModel(
                model_name,
                generation_config={"response_mime_type": "application/json"}
            )
            response = await model.generate_content_async(prompt + raw_text)
            data = json.loads(response.text)
            data.setdefault("confidence_score", 0.90)
            return data
        except Exception as e:
            logger.warning(f"Model {model_name} failed (likely rate limit): {e}")
            last_err = e

    raise last_err

async def extract_coi(raw_text: str, file_path: str = None) -> dict:
    """Extract COI fields using Gemini; fall back to mock on failure."""
    try:
        return await _call_gemini_with_fallback(COI_PROMPT, raw_text)
    except Exception as e:
        logger.warning(f"All Gemini models failed: {e} — using mock")
        return mock_extract_coi(raw_text)

async def extract_diversity(raw_text: str, file_path: str = None) -> dict:
    """Extract diversity cert fields using Gemini; fall back to mock on failure."""
    try:
        return await _call_gemini_with_fallback(DIVERSITY_PROMPT, raw_text)
    except Exception as e:
        logger.warning(f"All Gemini models failed: {e} — using mock")
        return mock_extract_diversity(raw_text)


# ── Mock extractors (regex-based fallbacks) ───────────────────

def mock_extract_coi(text: str) -> dict:
    text_lower = text.lower()

    # Insured name
    insured = None
    m = re.search(r"insured[:\s]+([A-Za-z0-9 ,\.]+)", text, re.IGNORECASE)
    if m:
        insured = m.group(1).strip()

    # Policy number
    policy = None
    m = re.search(r"policy\s*(?:number|no\.?)[:\s]+([A-Z0-9\-]+)", text, re.IGNORECASE)
    if m:
        policy = m.group(1).strip()

    # GL limit
    gl_limit = None
    m = re.search(r"general\s+liability.*?\$([0-9,]+)", text, re.IGNORECASE)
    if m:
        try:
            gl_limit = float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    # Expiry date
    expiry = None
    m = re.search(
        r"expir(?:ation|y|es)(?:\s+date)?[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE
    )
    if m:
        expiry = _normalise_date(m.group(1))

    return {
        "insured_name": insured,
        "insurer_name": None,
        "policy_number": policy,
        "coverage_type": "Commercial General Liability" if "general liability" in text_lower else None,
        "general_liability_limit_usd": gl_limit,
        "workers_comp_limit_usd": None,
        "auto_liability_limit_usd": None,
        "effective_date": None,
        "expiry_date": expiry,
        "additional_insured": "additional insured" in text_lower,
        "certificate_holder": None,
        "confidence_score": 0.85,
    }


def mock_extract_diversity(text: str) -> dict:
    text_lower = text.lower()

    # Cert type
    cert_type = None
    for t in ["MBE", "WBE", "DBE", "SBE", "SDVOSB", "VOSB", "HUBZone"]:
        if t.lower() in text_lower:
            cert_type = t
            break

    # Cert number
    cert_number = None
    m = re.search(r"cert(?:ificate)?\s*(?:number|no\.?)[:\s]+([A-Z0-9\-]+)", text, re.IGNORECASE)
    if m:
        cert_number = m.group(1).strip()

    # Ownership
    ownership = None
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%\s*owned", text, re.IGNORECASE)
    if m:
        try:
            ownership = float(m.group(1))
        except ValueError:
            pass
    if ownership is None and cert_type:
        ownership = 51.0  # assume minimum qualifying for mock

    # Expiry date
    expiry = None
    m = re.search(
        r"expir(?:ation|y|es)(?:\s+date)?[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE
    )
    if m:
        expiry = _normalise_date(m.group(1))

    # Cert body
    cert_body = None
    for body in ["NMSDC", "WBENC", "SBA", "USDOT", "NCTRCA", "city of"]:
        if body.lower() in text_lower:
            cert_body = body.upper()
            break

    return {
        "cert_body": cert_body,
        "cert_type": cert_type,
        "cert_number": cert_number,
        "ownership_pct": ownership,
        "expiry_date": expiry,
        "confidence_score": 0.85,
    }


def _normalise_date(raw: str) -> str | None:
    """Convert MM/DD/YYYY or MM-DD-YYYY → YYYY-MM-DD."""
    raw = raw.strip()
    for sep in ["/", "-"]:
        parts = raw.split(sep)
        if len(parts) == 3:
            m, d, y = parts
            if len(y) == 2:
                y = "20" + y
            try:
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                pass
    return None
