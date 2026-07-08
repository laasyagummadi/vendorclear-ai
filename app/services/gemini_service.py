import os
import json
import re
from loguru import logger
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not configured. Gemini service will run in offline Mock Mode.")

COI_DEFAULT = {
    "insured_name": None,
    "insurer_name": None,
    "policy_number": None,
    "coverage_type": None,
    "general_liability_limit_usd": None,
    "workers_comp_limit_usd": None,
    "auto_liability_limit_usd": None,
    "effective_date": None,
    "expiry_date": None,
    "additional_insured": False,
    "certificate_holder": None,
    "confidence_score": 0.0
}

DIVERSITY_DEFAULT = {
    "cert_body": None,
    "cert_type": None,
    "cert_number": None,
    "ownership_pct": None,
    "expiry_date": None,
    "confidence_score": 0.0
}

def clean_and_parse_json(text: str) -> dict:
    """Helper to clean markdown formatting and parse JSON response."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())

def mock_extract_coi(raw_text: str) -> dict:
    logger.info("Using mock extraction for COI document.")
    res = COI_DEFAULT.copy()
    if not raw_text.strip():
        return res
    res["confidence_score"] = 0.85
    
    # Regex matching for testing
    dates = re.findall(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", raw_text)
    if len(dates) >= 2:
        res["effective_date"] = dates[0]
        res["expiry_date"] = dates[1]
    elif len(dates) == 1:
        res["expiry_date"] = dates[0]

    insured_match = re.search(r"(?:INSURED|NAMED INSURED):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if insured_match:
        res["insured_name"] = insured_match.group(1).strip()
    
    insurer_match = re.search(r"(?:INSURER|INSURER [A-F]):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if insurer_match:
        res["insurer_name"] = insurer_match.group(1).strip()

    policy_match = re.search(r"(?:POLICY NUMBER|POLICY NUM):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if policy_match:
        res["policy_number"] = policy_match.group(1).strip()

    coverage_match = re.search(r"(?:COVERAGE|COVERAGE TYPE):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if coverage_match:
        res["coverage_type"] = coverage_match.group(1).strip()
    
    if "additional insured" in raw_text.lower() or "addl insr" in raw_text.lower() or "additional_insured: yes" in raw_text.lower() or "yes" in raw_text.lower():
        res["additional_insured"] = True
        
    limit_match = re.search(r"(?:LIMIT|LIMITS):\s*([0-9,]+)", raw_text, re.IGNORECASE)
    if limit_match:
        num_str = limit_match.group(1).replace(",", "")
        res["general_liability_limit_usd"] = float(num_str)

    return res

def mock_extract_diversity(raw_text: str) -> dict:
    logger.info("Using mock extraction for Diversity certificate.")
    res = DIVERSITY_DEFAULT.copy()
    if not raw_text.strip():
        return res
    res["confidence_score"] = 0.85

    dates = re.findall(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", raw_text)
    if dates:
        res["expiry_date"] = dates[-1]

    agency_match = re.search(r"(?:AGENCY|ORGANIZATION|ISSUER|BODY):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if agency_match:
        res["cert_body"] = agency_match.group(1).strip()

    cert_type_match = re.search(r"(?:CERTIFICATE TYPE|CERT TYPE|TYPE):\s*([^\n]+)", raw_text, re.IGNORECASE)
    if cert_type_match:
        res["cert_type"] = cert_type_match.group(1).strip()

    number_match = re.search(r"(?:NUMBER|CERTIFICATE NO):\s*([A-Za-z0-9-]+)", raw_text, re.IGNORECASE)
    if number_match:
        res["cert_number"] = number_match.group(1).strip()

    ownership_match = re.search(r"(?:OWNERSHIP|PERCENT|PERCENTAGE):\s*([0-9.]+)", raw_text, re.IGNORECASE)
    if ownership_match:
        res["ownership_pct"] = float(ownership_match.group(1))

    return res

async def extract_coi(raw_text: str) -> dict:
    """Call Gemini to extract COI fields, fallback to mock regex parser if error or key missing."""
    if not raw_text.strip():
        return COI_DEFAULT.copy()

    if not GEMINI_API_KEY:
        return mock_extract_coi(raw_text)

    prompt = f"""
    You are a document extraction assistant. Extract the following fields from the Certificate of Insurance (COI) text:
    - insured_name
    - insurer_name
    - policy_number
    - coverage_type (e.g. GENERAL LIABILITY)
    - general_liability_limit_usd (extract the General Liability limit, parse as number)
    - workers_comp_limit_usd (extract Workers Compensation limit, parse as number)
    - auto_liability_limit_usd (extract Auto Liability limit, parse as number)
    - effective_date (YYYY-MM-DD format)
    - expiry_date (YYYY-MM-DD format)
    - additional_insured (boolean: is the certificate holder listed as additional insured?)
    - certificate_holder (name of the certificate holder)
    
    Return a flat JSON object containing these keys. If a field is not found, return null for it.
    
    Document text:
    {raw_text}
    """
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        response = await model.generate_content_async(prompt)
        res = clean_and_parse_json(response.text)
        res["confidence_score"] = 0.90
        return res
    except Exception as e:
        logger.error(f"Gemini API COI extraction failed: {str(e)}. Falling back to mock extraction.")
        return mock_extract_coi(raw_text)

async def extract_diversity(raw_text: str) -> dict:
    """Call Gemini to extract Diversity Cert fields, fallback to mock regex parser if error or key missing."""
    if not raw_text.strip():
        return DIVERSITY_DEFAULT.copy()

    if not GEMINI_API_KEY:
        return mock_extract_diversity(raw_text)

    prompt = f"""
    You are a document extraction assistant. Extract the following fields from the Diversity Certification document text:
    - cert_body (agency or issuing body)
    - cert_type (e.g. MBE, WBE, DBE, SDVOB)
    - cert_number (certificate number)
    - ownership_pct (percentage of diverse ownership, parse as number, e.g. 51.0)
    - expiry_date (expiration date, YYYY-MM-DD format)
    
    Return a flat JSON object containing these keys. If a field is not found, return null for it.
    
    Document text:
    {raw_text}
    """
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        response = await model.generate_content_async(prompt)
        res = clean_and_parse_json(response.text)
        res["confidence_score"] = 0.90
        return res
    except Exception as e:
        logger.error(f"Gemini API Diversity extraction failed: {str(e)}. Falling back to mock extraction.")
        return mock_extract_diversity(raw_text)
