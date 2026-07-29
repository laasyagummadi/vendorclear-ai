"""
diagnose_dashboard_bug.py — find out why Vendor Health Score / Health Grade
Distribution shows "N/A" / empty on the Dashboard.

The Dashboard silently catches any exception from get_fleet_health_score()
and shows a blank fallback instead of the real error. This script re-checks
the exact conditions that function depends on, directly against the
database file, so you can see the bad row without needing to read a
Python traceback in your terminal.

Usage (from the backend/ folder, where vendorclear.db lives):
    python3 diagnose_dashboard_bug.py
    python3 diagnose_dashboard_bug.py /path/to/other.db
"""
import sqlite3
import sys
from datetime import date

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "vendorclear.db"

VALID_VENDOR_STATUS = {"COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT"}
VALID_RISK_TIER = {"LOW", "MEDIUM", "HIGH"}
VALID_DOC_TYPE = {"COI", "DIVERSITY_CERT", "UNKNOWN"}
VALID_DOC_STATUS = {"PENDING", "PROCESSING", "PROCESSED", "FAILED"}
VALID_ANALYSIS_STATUS = {"COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT"}
VALID_FINDING_SEVERITY = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def is_valid_iso_date_or_none(val):
    if val is None or val == "":
        return True
    try:
        date.fromisoformat(val)
        return True
    except ValueError:
        return False


def main():
    print(f"Checking: {DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    problems = []

    # ── Vendors ──────────────────────────────────────────────
    cur.execute("SELECT id, name, status, risk_tier, gl_expiry, wc_expiry, is_active FROM vendors")
    vendors = cur.fetchall()
    active_vendor_ids = set()
    for vid, name, status, risk_tier, gl, wc, is_active in vendors:
        if is_active:
            active_vendor_ids.add(vid)
        if status not in VALID_VENDOR_STATUS:
            problems.append(f"Vendor '{name}' (id={vid}) has invalid status: {status!r}")
        if risk_tier not in VALID_RISK_TIER:
            problems.append(f"Vendor '{name}' (id={vid}) has invalid risk_tier: {risk_tier!r}")
        if not is_valid_iso_date_or_none(gl):
            problems.append(f"Vendor '{name}' (id={vid}) has non-ISO gl_expiry: {gl!r}")
        if not is_valid_iso_date_or_none(wc):
            problems.append(f"Vendor '{name}' (id={vid}) has non-ISO wc_expiry: {wc!r}")

    print(f"Vendors checked: {len(vendors)} ({len(active_vendor_ids)} active)")

    # ── Documents ────────────────────────────────────────────
    cur.execute("SELECT id, vendor_id, document_type, status, filename FROM documents")
    documents = cur.fetchall()
    vendor_ids_all = {v[0] for v in vendors}
    for did, vendor_id, doc_type, status, filename in documents:
        if doc_type not in VALID_DOC_TYPE:
            problems.append(f"Document '{filename}' (id={did}) has invalid document_type: {doc_type!r}")
        if status not in VALID_DOC_STATUS:
            problems.append(f"Document '{filename}' (id={did}) has invalid status: {status!r}")
        if vendor_id not in vendor_ids_all:
            problems.append(f"Document '{filename}' (id={did}) points to missing vendor_id: {vendor_id!r}")

    print(f"Documents checked: {len(documents)}")

    # ── Analyses ─────────────────────────────────────────────
    cur.execute("SELECT id, document_id, status FROM analyses")
    analyses = cur.fetchall()
    document_ids_all = {d[0] for d in documents}
    for aid, document_id, status in analyses:
        if status not in VALID_ANALYSIS_STATUS:
            problems.append(f"Analysis (id={aid}) has invalid status: {status!r}")
        if document_id not in document_ids_all:
            problems.append(f"Analysis (id={aid}) points to missing document_id: {document_id!r}")

    print(f"Analyses checked: {len(analyses)}")

    # ── Findings ─────────────────────────────────────────────
    cur.execute("SELECT id, analysis_id, severity, rule_code FROM findings")
    findings = cur.fetchall()
    analysis_ids_all = {a[0] for a in analyses}
    for fid, analysis_id, severity, rule_code in findings:
        if severity not in VALID_FINDING_SEVERITY:
            problems.append(f"Finding '{rule_code}' (id={fid}) has invalid severity: {severity!r}")
        if analysis_id not in analysis_ids_all:
            problems.append(f"Finding '{rule_code}' (id={fid}) points to missing analysis_id: {analysis_id!r}")

    print(f"Findings checked: {len(findings)}\n")

    # ── Result ───────────────────────────────────────────────
    if problems:
        print(f"FOUND {len(problems)} PROBLEM(S) — any of these will crash the health score calc:\n")
        for p in problems:
            print(" -", p)
    else:
        print("No data problems found. If the Dashboard still shows N/A, the bug is in the")
        print("code itself rather than the data — check the backend terminal/log output for a")
        print("line starting with: 'get_fleet_health_score() failed while building dashboard")
        print("summary:' and share that exact line.")

    conn.close()


if __name__ == "__main__":
    main()
