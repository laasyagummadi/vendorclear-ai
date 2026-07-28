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
            "gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )
        logger.info("Gemini 1.5 Flash model initialized")
    except Exception as e:
        logger.warning(f"Gemini init failed, using mock: {e}")


# ── COI extraction ────────────────────────────────────────────

COI_PROMPT = """
Extract the following fields from this Certificate of Insurance (COI) text and return ONLY a JSON object.
Look carefully through the ENTIRE document — insured name, producer, address blocks, and contact lines
often contain the vendor's contact details. Extract whatever is present; use null only when truly absent.
{
  "insured_name": string or null,
  "insurer_name": string or null,
  "policy_number": string or null,
  "coverage_type": string or null,
  "general_liability_limit_usd": number or null,
  "workers_comp_limit_usd": number or null,
  "workers_comp_expiry_date": "YYYY-MM-DD" or null,
  "auto_liability_limit_usd": number or null,
  "effective_date": "YYYY-MM-DD" or null,
  "expiry_date": "YYYY-MM-DD" or null,
  "additional_insured": boolean or null,
  "certificate_holder": string or null,
  "contact_name": string or null (the named contact / authorized representative for the insured),
  "email": string or null (any email address for the insured/vendor),
  "phone": string or null (any phone/fax number for the insured/vendor),
  "address": string or null (street address of the insured/vendor),
  "city": string or null,
  "state": string or null (2-letter code if possible),
  "zip_code": string or null,
  "confidence_score": number between 0.0 and 1.0
}

COI Text:
"""

DIVERSITY_PROMPT = """
Extract the following fields from this Diversity/Minority Business Certificate text and return ONLY a JSON object.
Look through the whole document for the certified business's contact and address details too.
{
  "cert_body": string or null,
  "cert_type": string or null (e.g. "MBE", "WBE", "DBE", "SBE"),
  "cert_number": string or null,
  "ownership_pct": number or null (percentage 0-100),
  "expiry_date": "YYYY-MM-DD" or null,
  "contact_name": string or null,
  "email": string or null,
  "phone": string or null,
  "address": string or null,
  "city": string or null,
  "state": string or null,
  "zip_code": string or null,
  "confidence_score": number between 0.0 and 1.0
}

Certificate Text:
"""


async def extract_coi(raw_text: str) -> dict:
    """Extract COI fields using Gemini; fall back to mock on failure."""
    if _model and raw_text.strip():
        try:
            response = await _model.generate_content_async(COI_PROMPT + raw_text)
            data = json.loads(response.text)
            data.setdefault("confidence_score", 0.90)
            return data
        except Exception as e:
            logger.warning(f"Gemini COI extraction failed: {e} — using mock")
    return mock_extract_coi(raw_text)


async def extract_diversity(raw_text: str) -> dict:
    """Extract diversity cert fields using Gemini; fall back to mock on failure."""
    if _model and raw_text.strip():
        try:
            response = await _model.generate_content_async(DIVERSITY_PROMPT + raw_text)
            data = json.loads(response.text)
            data.setdefault("confidence_score", 0.90)
            return data
        except Exception as e:
            logger.warning(f"Gemini diversity extraction failed: {e} — using mock")
    return mock_extract_diversity(raw_text)


# ── Mock extractors (regex-based fallbacks) ───────────────────

def _extract_contact_fields(text: str) -> dict:
    """Best-effort extraction of vendor contact/address details from raw
    document text. Used by both fallback extractors so the vendor profile
    auto-fills even when Gemini is not configured."""
    out = {
        "contact_name": None, "email": None, "phone": None,
        "address": None, "city": None, "state": None, "zip_code": None,
    }

    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if m:
        out["email"] = m.group(0).strip().rstrip(".")

    # Phone: (123) 456-7890, 123-456-7890, 123.456.7890, +1 123 456 7890
    m = re.search(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    if m:
        out["phone"] = m.group(0).strip()

    m = re.search(
        r"(?:authorized\s+representative|contact|attn|attention|agent)[:\s]+"
        r"([A-Z][A-Za-z.'-]+(?:[ \t]+[A-Z][A-Za-z.'-]+){1,2})",
        text, re.IGNORECASE,
    )
    if m:
        # stop at a newline and strip any trailing label word that leaked in
        name = m.group(1).split("\n")[0].strip()
        out["contact_name"] = name

    # Address line: "123 Main St, City, ST 12345"
    m = re.search(
        r"(\d{1,6}\s+[A-Za-z0-9.\s]+?(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Way|Ct|Court|Pl|Plaza)\.?)"
        r"\s*,?\s*([A-Za-z .'-]+?)\s*,\s*([A-Z]{2})\s+(\d{5})",
        text,
    )
    if m:
        out["address"] = m.group(1).strip()
        out["city"] = m.group(2).strip()
        out["state"] = m.group(3).strip()
        out["zip_code"] = m.group(4).strip()
    else:
        # Looser: "City, ST 12345" anywhere
        m2 = re.search(r"([A-Za-z][A-Za-z .'-]+?)\s*,\s*([A-Z]{2})\s+(\d{5})", text)
        if m2:
            out["city"] = m2.group(1).strip()
            out["state"] = m2.group(2).strip()
            out["zip_code"] = m2.group(3).strip()

    return out


def mock_extract_coi(text: str) -> dict:
    text_lower = text.lower()

    # Insured name
    insured = None
    m = re.search(r"insured[:\s]+([A-Za-z0-9 ,\.]+)", text, re.IGNORECASE)
    if m:
        insured = m.group(1).split("\n")[0].strip()

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
        r"expir(?:ation|y|es)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE
    )
    if m:
        expiry = _normalise_date(m.group(1))

    # Workers Comp expiry (may appear as its own line)
    wc_expiry = None
    m = re.search(
        r"workers?\s*comp(?:ensation)?.{0,60}?expir(?:ation|y|es)?[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        wc_expiry = _normalise_date(m.group(1))

    result = {
        "insured_name": insured,
        "insurer_name": None,
        "policy_number": policy,
        "coverage_type": "Commercial General Liability" if "general liability" in text_lower else None,
        "general_liability_limit_usd": gl_limit,
        "workers_comp_limit_usd": None,
        "workers_comp_expiry_date": wc_expiry,
        "auto_liability_limit_usd": None,
        "effective_date": None,
        "expiry_date": expiry,
        "additional_insured": "additional insured" in text_lower,
        "certificate_holder": None,
        "confidence_score": 0.85,
    }
    result.update(_extract_contact_fields(text))
    return result


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
        r"expir(?:ation|y|es)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE
    )
    if m:
        expiry = _normalise_date(m.group(1))

    # Cert body
    cert_body = None
    for body in ["NMSDC", "WBENC", "SBA", "USDOT", "NCTRCA", "city of"]:
        if body.lower() in text_lower:
            cert_body = body.upper()
            break

    result = {
        "cert_body": cert_body,
        "cert_type": cert_type,
        "cert_number": cert_number,
        "ownership_pct": ownership,
        "expiry_date": expiry,
        "confidence_score": 0.85,
    }
    result.update(_extract_contact_fields(text))
    return result


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
