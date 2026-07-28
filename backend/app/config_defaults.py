# ─────────────────────────────────────────────────────────────
#  app/config_defaults.py  —  Default version configuration values
# ─────────────────────────────────────────────────────────────
"""
Single source of truth for the application's *configurable* settings.

Every setting here is admin-editable at runtime (stored in the
version_configs table). This module only defines the DEFAULTS used to
seed a fresh database and to validate incoming config keys.

The config is intentionally a flat dict of primitive values so that
NEW configurable parameters can be added later without a schema
migration (requirement 7 — "any future configurable modules").
"""

# Amounts are in Indian Rupees (₹) for the compensation field; insurance
# limits remain in USD to match the certificate documents the app reads.

CONFIG_SCHEMA = {
    # key: (label, type, help text)
    "compliance_compensation_inr": ("Compliance Compensation Amount (₹)", "int", "Payout amount for a compliance event."),
    "required_gl_limit_usd": ("Required General Liability Limit ($)", "int", "Minimum GL coverage a vendor must carry."),
    "required_wc_limit_usd": ("Required Workers Comp Limit ($)", "int", "Minimum Workers Compensation coverage."),
    "required_auto_limit_usd": ("Required Auto Liability Limit ($)", "int", "Minimum automobile liability coverage."),
    "min_ownership_percent": ("Minimum Diversity Ownership (%)", "int", "Minimum ownership % to qualify a diversity certification."),
    "expiry_warning_days": ("Expiry Warning Window (days)", "int", "Flag certificates expiring within this many days."),
    "expiry_critical_days": ("Expiry Critical Window (days)", "int", "Escalate certificates expiring within this many days."),
    "min_confidence_score": ("Minimum Extraction Confidence", "float", "Below this, an analysis is flagged for review (0.0–1.0)."),
    "require_additional_insured": ("Require 'Additional Insured'", "bool", "Vendor's COI must name the company as additional insured."),
}

# ── Version 1 defaults ─────────────────────────────────────────
VERSION_1_DEFAULTS = {
    "compliance_compensation_inr": 500000,      # ₹5,00,000
    "required_gl_limit_usd": 1000000,
    "required_wc_limit_usd": 500000,
    "required_auto_limit_usd": 1000000,
    "min_ownership_percent": 51,
    "expiry_warning_days": 30,
    "expiry_critical_days": 7,
    "min_confidence_score": 0.70,
    "require_additional_insured": True,
}

# ── Version 2 defaults ─────────────────────────────────────────
VERSION_2_DEFAULTS = {
    "compliance_compensation_inr": 1000000,     # ₹10,00,000
    "required_gl_limit_usd": 1000000,
    "required_wc_limit_usd": 500000,
    "required_auto_limit_usd": 1000000,
    "min_ownership_percent": 51,
    "expiry_warning_days": 30,
    "expiry_critical_days": 7,
    "min_confidence_score": 0.70,
    "require_additional_insured": True,
}

DEFAULTS_BY_VERSION = {
    1: VERSION_1_DEFAULTS,
    2: VERSION_2_DEFAULTS,
}


def coerce_value(key: str, value):
    """Coerce an incoming config value to the type declared in CONFIG_SCHEMA."""
    if key not in CONFIG_SCHEMA:
        raise ValueError(f"Unknown configuration key: {key}")
    _, typ, _ = CONFIG_SCHEMA[key]
    if typ == "int":
        return int(value)
    if typ == "float":
        return float(value)
    if typ == "bool":
        return bool(value)
    return value
