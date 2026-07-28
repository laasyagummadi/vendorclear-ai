"""
scripts/seed_data.py — Demo seed data for VendorClear AI

Populates the database with a demo user and a realistic spread of vendors
across categories/compliance states, so the dashboard, vendor list, alerts,
and compliance report all have real data to render instead of empty states.

Usage:
    cd backend
    python -m scripts.seed_data
"""
import asyncio
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from app.database import AsyncSessionLocal, engine
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.vendor import Vendor, VendorStatus, RiskTier, VendorCategory, VendorType
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.models.finding import Finding, FindingSeverity
from app.utils.security import hash_password


def d(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


VENDORS = [
    # ── Electronics ──────────────────────────────────────────
    dict(name="Circuit Dynamics Inc.", contact_name="Priya Raman", email="priya@circuitdynamics.com",
         phone="512-555-0142", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(180), wc_expiry=d(200), diversity_types=["MBE"],
         notes="Primary supplier for grid sensor hardware.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUPPLIER,
         business_unit="Grid Operations", region="Southwest", insurance_provider="Travelers",
         assigned_analyst_id="__ANALYST_2__"),
    dict(name="Voltage Components LLC", contact_name="Mark Delgado", email="mark@voltagecomponents.com",
         phone="619-555-0110", city="San Diego", state="CA", zip_code="92101",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(18), wc_expiry=d(90), diversity_types=None,
         notes="GL certificate expiring soon — follow up requested.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUPPLIER,
         business_unit="Grid Operations", region="West", insurance_provider="Liberty Mutual",
         assigned_analyst_id="__ANALYST_1__"),

    # ── Grocery / Food Service ───────────────────────────────
    dict(name="Harvest Point Foods", contact_name="Lena Cho", email="lena@harvestpointfoods.com",
         phone="303-555-0177", city="Denver", state="CO", zip_code="80202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(240), wc_expiry=d(210), diversity_types=["WBE"],
         notes="Cafeteria catering contract, renews annually.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="Mountain", insurance_provider="The Hartford",
         assigned_analyst_id="__ANALYST_1__"),

    # ── Fashion ───────────────────────────────────────────────
    dict(name="Meridian Uniform Supply", contact_name="Oscar Reyes", email="oscar@meridianuniforms.com",
         phone="214-555-0199", city="Dallas", state="TX", zip_code="75201",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-14), wc_expiry=d(-5), diversity_types=["HUBZone"],
         notes="Insurance lapsed — field crew uniforms on hold pending renewal.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Field Operations", region="South Central", insurance_provider="Nationwide",
         assigned_analyst_id="__ANALYST_2__"),

    # ── Furniture ─────────────────────────────────────────────
    dict(name="Redwood Office Furnishings", contact_name="Grace Lin", email="grace@redwoodoffice.com",
         phone="415-555-0133", city="San Francisco", state="CA", zip_code="94105",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(300), wc_expiry=d(300), diversity_types=None,
         notes="Office buildout vendor for regional facilities.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="West", insurance_provider="The Hartford",
         assigned_analyst_id="__ANALYST_1__"),

    # ── Pharmacy / Medical Supply ────────────────────────────
    dict(name="ClearPath Medical Supply", contact_name="Dr. Sam Okafor", email="sam@clearpathmed.com",
         phone="404-555-0166", city="Atlanta", state="GA", zip_code="30303",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(45), wc_expiry=d(6), diversity_types=["MBE", "SBE"],
         notes="Workers comp expiring within a week — urgent renewal needed.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Safety & Compliance", region="Southeast", insurance_provider="Chubb",
         assigned_analyst_id="__ANALYST_2__"),

    # ── Restaurants (on-site vending / crew catering) ───────
    dict(name="Blue Ridge Catering Co.", contact_name="Tasha Brooks", email="tasha@blueridgecatering.com",
         phone="828-555-0121", city="Asheville", state="NC", zip_code="28801",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(150), wc_expiry=d(150), diversity_types=["WBE", "DBE"],
         notes="Crew catering for field operations.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="Field Operations", region="Southeast", insurance_provider="Nationwide",
         assigned_analyst_id="__ANALYST_1__"),

    # ── Home Services / Field Contractors ────────────────────
    dict(name="Ironclad Line Services", contact_name="Bill Harrington", email="bill@ironcladline.com",
         phone="602-555-0155", city="Phoenix", state="AZ", zip_code="85003",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-30), wc_expiry=d(120), diversity_types=None,
         notes="GL policy expired 30 days ago — high-risk field contractor, escalate.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest", insurance_provider="Zurich",
         assigned_analyst_id="__ANALYST_2__"),
    dict(name="Summit Vegetation Management", contact_name="Renee Park", email="renee@summitveg.com",
         phone="503-555-0188", city="Portland", state="OR", zip_code="97201",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(25), wc_expiry=d(25), diversity_types=["VOSB"],
         notes="Right-of-way clearing crew, renewal in progress.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Pacific Northwest", insurance_provider="Liberty Mutual",
         assigned_analyst_id="__ANALYST_1__"),

    # ── Local Shops / Small Business ──────────────────────────
    dict(name="Prairie Hardware & Supply", contact_name="Wendell Moss", email="wendell@prairiehardware.com",
         phone="316-555-0144", city="Wichita", state="KS", zip_code="67202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(200), wc_expiry=d(200), diversity_types=["SBE"],
         notes="Local materials supplier, long-standing relationship.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="Midwest", insurance_provider="The Hartford",
         assigned_analyst_id="__ANALYST_2__"),

    # ── Health Grade distribution test set (VendorClearAI_Sample_Vendors.pdf) ─
    # Each of these 5 also gets one PROCESSED "COI" document and one PROCESSED
    # "Diversity Cert" document seeded below (see HEALTH_GRADE_TEST_DOCS), so
    # document_score (0-30) is present and the computed grade matches the
    # "Expected Health Grade" column in the PDF.
    dict(name="Apex Construction Services", contact_name="Test QA", email="qa+apex@vendorclear.ai",
         phone="000-000-0001", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry="2027-12-31", wc_expiry="2027-12-31", diversity_types=["MBE", "WBE"],
         notes="Health Grade test vendor — expected grade A.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest", insurance_provider="Travelers",
         assigned_analyst_id="__ANALYST_1__"),
    dict(name="GreenTech Solutions", contact_name="Test QA", email="qa+greentech@vendorclear.ai",
         phone="000-000-0002", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry="2026-09-15", wc_expiry="2026-09-15", diversity_types=["WBE"],
         notes="Health Grade test vendor — expected grade B.",
         category=VendorCategory.SOFTWARE, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="IT & Platform", region="Southwest", insurance_provider="Chubb",
         assigned_analyst_id="__ANALYST_2__"),
    dict(name="Metro Electrical Contractors", contact_name="Test QA", email="qa+metro@vendorclear.ai",
         phone="000-000-0003", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry="2026-08-15", wc_expiry="2026-08-15", diversity_types=None,
         notes="Health Grade test vendor — expected grade C.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Grid Operations", region="Southwest", insurance_provider="Zurich",
         assigned_analyst_id="__ANALYST_1__"),
    dict(name="Sunrise Logistics", contact_name="Test QA", email="qa+sunrise@vendorclear.ai",
         phone="000-000-0004", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.HIGH,
         gl_expiry="2026-07-25", wc_expiry="2026-07-28", diversity_types=None,
         notes="Health Grade test vendor — expected grade D.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="Field Operations", region="Southwest", insurance_provider="Nationwide",
         assigned_analyst_id="__ANALYST_2__"),
    dict(name="Alpha Industrial Works", contact_name="Test QA", email="qa+alpha@vendorclear.ai",
         phone="000-000-0005", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry="2026-05-10", wc_expiry="2026-04-15", diversity_types=None,
         notes="Health Grade test vendor — expected grade F.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest", insurance_provider="Liberty Mutual",
         assigned_analyst_id="__ANALYST_1__"),
]


# Each health-grade test vendor needs one PROCESSED COI + one PROCESSED
# Diversity Cert document so document_score (0-30) is reachable and the
# computed grade matches the PDF's "Expected Health Grade" column.
HEALTH_GRADE_TEST_DOCS = {
    "Apex Construction Services": ["Apex_COI.pdf", "Apex_Diversity_Certificate.pdf"],
    "GreenTech Solutions": ["GreenTech_COI.pdf", "GreenTech_Diversity_Certificate.pdf"],
    "Metro Electrical Contractors": ["Metro_COI.pdf", "Metro_Diversity_Certificate.pdf"],
    "Sunrise Logistics": ["Sunrise_COI.pdf", "Sunrise_Diversity_Certificate.pdf"],
    "Alpha Industrial Works": ["Alpha_COI.pdf", "Alpha_Diversity_Certificate.pdf"],
}


# Sample findings (Nirupama's Analytics — Module 9 "most common violations")
# attached to the COI document of a few health-grade test vendors, so the
# Analytics page has real, non-empty violation data to demonstrate rather
# than an empty state on a fresh seed.
SAMPLE_FINDINGS = {
    "Metro Electrical Contractors": [
        ("GL_LIMIT_BELOW_POLICY_MIN", FindingSeverity.MEDIUM,
         "General liability limit is below the $3M minimum required for the Electrical policy."),
    ],
    "Sunrise Logistics": [
        ("WC_EXPIRING_SOON", FindingSeverity.HIGH,
         "Workers compensation coverage expires within the policy's warning window."),
        ("MISSING_ADDITIONAL_INSURED", FindingSeverity.MEDIUM,
         "Certificate does not list the client as an additional insured."),
    ],
    "Alpha Industrial Works": [
        ("GL_EXPIRED", FindingSeverity.CRITICAL,
         "General liability coverage has already expired."),
        ("MISSING_ADDITIONAL_INSURED", FindingSeverity.HIGH,
         "Certificate does not list the client as an additional insured."),
    ],
}


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Demo user
        from sqlalchemy import select
        existing = await db.execute(select(User).where(User.email == "demo@vendorclear.ai"))
        demo_user = existing.scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                email="demo@vendorclear.ai",
                full_name="Demo Admin",
                hashed_password=hash_password("DemoPass123"),
                is_admin=True,
                role=UserRole.ADMIN,
            )
            db.add(demo_user)
            await db.flush()
            print(f"Created demo user: demo@vendorclear.ai / DemoPass123")
        else:
            print("Demo user already exists, skipping.")

        # Two analyst users vendors get assigned to, so the "Assigned Analyst"
        # filter has real, distinct options to demonstrate.
        async def get_or_create_analyst(email: str, full_name: str) -> User:
            existing_a = await db.execute(select(User).where(User.email == email))
            analyst = existing_a.scalar_one_or_none()
            if not analyst:
                analyst = User(
                    email=email, full_name=full_name,
                    hashed_password=hash_password("DemoPass123"),
                    is_admin=False,
                    role=UserRole.ANALYST,
                )
                db.add(analyst)
                await db.flush()
                print(f"Created analyst user: {email} / DemoPass123")
            return analyst

        analyst1 = await get_or_create_analyst("nirupama@vendorclear.ai", "Nirupama Iyer")
        analyst2 = await get_or_create_analyst("hruthi@vendorclear.ai", "Hruthi Rao")
        analyst_ids = {"__ANALYST_1__": analyst1.id, "__ANALYST_2__": analyst2.id}

        # One demo login per role (Feature 7 / RBAC) so all four permission
        # levels can be demoed without registering new accounts by hand.
        async def get_or_create_user(email: str, full_name: str, role: UserRole) -> User:
            existing_u = await db.execute(select(User).where(User.email == email))
            u = existing_u.scalar_one_or_none()
            if not u:
                u = User(
                    email=email, full_name=full_name,
                    hashed_password=hash_password("DemoPass123"),
                    is_admin=(role == UserRole.ADMIN),
                    role=role,
                )
                db.add(u)
                await db.flush()
                print(f"Created {role.value.lower()} user: {email} / DemoPass123")
            return u

        await get_or_create_user("vendor.demo@vendorclear.ai", "Vendor Demo User", UserRole.VENDOR)
        await get_or_create_user("auditor.demo@vendorclear.ai", "Auditor Demo User", UserRole.AUDITOR)

        created = 0
        for v in VENDORS:
            existing_v = await db.execute(select(Vendor).where(Vendor.name == v["name"]))
            vendor = existing_v.scalar_one_or_none()
            if vendor:
                continue
            v = dict(v)
            if v.get("assigned_analyst_id") in analyst_ids:
                v["assigned_analyst_id"] = analyst_ids[v["assigned_analyst_id"]]
            vendor = Vendor(**v, created_by_id=demo_user.id)
            db.add(vendor)
            await db.flush()
            created += 1

            doc_filenames = HEALTH_GRADE_TEST_DOCS.get(v["name"])
            coi_doc = None
            if doc_filenames:
                coi_filename, diversity_filename = doc_filenames
                coi_doc = Document(
                    vendor_id=vendor.id,
                    filename=coi_filename,
                    file_path=f"uploads/seed/{coi_filename}",
                    file_size_bytes=1024,
                    mime_type="application/pdf",
                    document_type=DocumentType.COI,
                    status=DocumentStatus.PROCESSED,
                )
                db.add(coi_doc)
                db.add(Document(
                    vendor_id=vendor.id,
                    filename=diversity_filename,
                    file_path=f"uploads/seed/{diversity_filename}",
                    file_size_bytes=1024,
                    mime_type="application/pdf",
                    document_type=DocumentType.DIVERSITY_CERT,
                    status=DocumentStatus.PROCESSED,
                ))

            findings_for_vendor = SAMPLE_FINDINGS.get(v["name"])
            if findings_for_vendor and coi_doc is not None:
                await db.flush()  # coi_doc.id needs to exist before Analysis references it
                analysis_status = (
                    AnalysisStatus.NON_COMPLIANT if vendor.status == VendorStatus.NON_COMPLIANT
                    else AnalysisStatus.NEEDS_REVIEW
                )
                analysis = Analysis(
                    document_id=coi_doc.id,
                    confidence_score=0.92,
                    status=analysis_status,
                )
                db.add(analysis)
                await db.flush()
                for rule_code, severity, message in findings_for_vendor:
                    db.add(Finding(
                        analysis_id=analysis.id,
                        severity=severity,
                        rule_code=rule_code,
                        message=message,
                    ))

        await db.commit()
        print(f"Seeded {created} vendors ({len(VENDORS) - created} already existed).")
        print("\nDemo logins (all use password DemoPass123):")
        print("  Admin:    demo@vendorclear.ai")
        print("  Analyst:  nirupama@vendorclear.ai / hruthi@vendorclear.ai")
        print("  Vendor:   vendor.demo@vendorclear.ai")
        print("  Auditor:  auditor.demo@vendorclear.ai")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
