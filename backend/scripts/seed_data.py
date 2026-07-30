"""
scripts/seed_data.py — Demo seed data for VendorClear AI
=========================================================
Merged from all three team versions (Hruthi/Laasya/Nirupama).
Includes: 15 vendors, documents, analyses, findings, RBAC demo users.

Usage:
    cd backend
    python -m scripts.seed_data

Credentials after seeding:
    Admin:    admin@vendorclear.com   / admin123
    Analyst:  hruthi@vendorclear.ai  / DemoPass123
    Analyst:  nirupama@vendorclear.ai / DemoPass123
    Vendor:   vendor.demo@vendorclear.ai / DemoPass123
    Auditor:  auditor.demo@vendorclear.ai / DemoPass123
"""
import asyncio
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from sqlalchemy import select, text
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


# ─── Vendor data ─────────────────────────────────────────────────────────────
VENDORS = [
    # ── Electronics ──────────────────────────────────────────────────────────
    dict(name="Circuit Dynamics Inc.", contact_name="Priya Raman",
         email="priya@circuitdynamics.com", phone="512-555-0142",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(180), wc_expiry=d(200), diversity_types=["MBE"],
         notes="Primary supplier for grid sensor hardware.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUPPLIER,
         business_unit="Grid Operations", region="Southwest",
         insurance_provider="Travelers", assigned_analyst_id="__ANALYST_2__"),
    dict(name="Voltage Components LLC", contact_name="Mark Delgado",
         email="mark@voltagecomponents.com", phone="619-555-0110",
         city="San Diego", state="CA", zip_code="92101",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(18), wc_expiry=d(90), diversity_types=None,
         notes="GL certificate expiring soon — follow up requested.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUPPLIER,
         business_unit="Grid Operations", region="West",
         insurance_provider="Liberty Mutual", assigned_analyst_id="__ANALYST_1__"),

    # ── Grocery / Food Service ────────────────────────────────────────────────
    dict(name="Harvest Point Foods", contact_name="Lena Cho",
         email="lena@harvestpointfoods.com", phone="303-555-0177",
         city="Denver", state="CO", zip_code="80202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(240), wc_expiry=d(210), diversity_types=["WBE"],
         notes="Cafeteria catering contract, renews annually.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="Mountain",
         insurance_provider="The Hartford", assigned_analyst_id="__ANALYST_1__"),

    # ── Uniform / Fashion ─────────────────────────────────────────────────────
    dict(name="Meridian Uniform Supply", contact_name="Oscar Reyes",
         email="oscar@meridianuniforms.com", phone="214-555-0199",
         city="Dallas", state="TX", zip_code="75201",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-14), wc_expiry=d(-5), diversity_types=["HUBZone"],
         notes="Insurance lapsed — field crew uniforms on hold pending renewal.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Field Operations", region="South Central",
         insurance_provider="Nationwide", assigned_analyst_id="__ANALYST_2__"),

    # ── Furniture ─────────────────────────────────────────────────────────────
    dict(name="Redwood Office Furnishings", contact_name="Grace Lin",
         email="grace@redwoodoffice.com", phone="415-555-0133",
         city="San Francisco", state="CA", zip_code="94105",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(300), wc_expiry=d(300), diversity_types=None,
         notes="Office buildout vendor for regional facilities.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="West",
         insurance_provider="The Hartford", assigned_analyst_id="__ANALYST_1__"),

    # ── Medical Supply ────────────────────────────────────────────────────────
    dict(name="ClearPath Medical Supply", contact_name="Dr. Sam Okafor",
         email="sam@clearpathmed.com", phone="404-555-0166",
         city="Atlanta", state="GA", zip_code="30303",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(45), wc_expiry=d(6), diversity_types=["MBE", "SBE"],
         notes="Workers comp expiring within a week — urgent renewal needed.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Safety & Compliance", region="Southeast",
         insurance_provider="Chubb", assigned_analyst_id="__ANALYST_2__"),

    # ── Catering / Food Service ───────────────────────────────────────────────
    dict(name="Blue Ridge Catering Co.", contact_name="Tasha Brooks",
         email="tasha@blueridgecatering.com", phone="828-555-0121",
         city="Asheville", state="NC", zip_code="28801",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(150), wc_expiry=d(150), diversity_types=["WBE", "DBE"],
         notes="Crew catering for field operations.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="Field Operations", region="Southeast",
         insurance_provider="Nationwide", assigned_analyst_id="__ANALYST_1__"),

    # ── Field Contractors ─────────────────────────────────────────────────────
    dict(name="Ironclad Line Services", contact_name="Bill Harrington",
         email="bill@ironcladline.com", phone="602-555-0155",
         city="Phoenix", state="AZ", zip_code="85003",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-30), wc_expiry=d(120), diversity_types=None,
         notes="GL policy expired 30 days ago — high-risk field contractor, escalate.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest",
         insurance_provider="Zurich", assigned_analyst_id="__ANALYST_2__"),
    dict(name="Summit Vegetation Management", contact_name="Renee Park",
         email="renee@summitveg.com", phone="503-555-0188",
         city="Portland", state="OR", zip_code="97201",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(25), wc_expiry=d(25), diversity_types=["VOSB"],
         notes="Right-of-way clearing crew, renewal in progress.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Pacific Northwest",
         insurance_provider="Liberty Mutual", assigned_analyst_id="__ANALYST_1__"),

    # ── Local / Small Business ────────────────────────────────────────────────
    dict(name="Prairie Hardware & Supply", contact_name="Wendell Moss",
         email="wendell@prairiehardware.com", phone="316-555-0144",
         city="Wichita", state="KS", zip_code="67202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(200), wc_expiry=d(200), diversity_types=["SBE"],
         notes="Local materials supplier, long-standing relationship.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SUPPLIER,
         business_unit="Facilities", region="Midwest",
         insurance_provider="The Hartford", assigned_analyst_id="__ANALYST_2__"),

    # ── Health Grade test set ─────────────────────────────────────────────────
    dict(name="Apex Construction Services", contact_name="QA Team",
         email="qa+apex@vendorclear.ai", phone="000-000-0001",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry="2027-12-31", wc_expiry="2027-12-31",
         diversity_types=["MBE", "WBE"],
         notes="Health Grade test vendor — expected grade A.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest",
         insurance_provider="Travelers", assigned_analyst_id="__ANALYST_1__"),
    dict(name="GreenTech Solutions", contact_name="QA Team",
         email="qa+greentech@vendorclear.ai", phone="000-000-0002",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(47), wc_expiry=d(47), diversity_types=["WBE"],
         notes="Health Grade test vendor — expected grade B.",
         category=VendorCategory.SOFTWARE, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="IT & Platform", region="Southwest",
         insurance_provider="Chubb", assigned_analyst_id="__ANALYST_2__"),
    dict(name="Metro Electrical Contractors", contact_name="QA Team",
         email="qa+metro@vendorclear.ai", phone="000-000-0003",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(16), wc_expiry=d(16), diversity_types=None,
         notes="Health Grade test vendor — expected grade C.",
         category=VendorCategory.ELECTRICAL, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Grid Operations", region="Southwest",
         insurance_provider="Zurich", assigned_analyst_id="__ANALYST_1__"),
    dict(name="Sunrise Logistics", contact_name="QA Team",
         email="qa+sunrise@vendorclear.ai", phone="000-000-0004",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.HIGH,
         gl_expiry=d(4), wc_expiry=d(4), diversity_types=None,
         notes="Health Grade test vendor — expected grade D.",
         category=VendorCategory.OTHER, vendor_type=VendorType.SERVICE_PROVIDER,
         business_unit="Field Operations", region="Southwest",
         insurance_provider="Nationwide", assigned_analyst_id="__ANALYST_2__"),
    dict(name="Alpha Industrial Works", contact_name="QA Team",
         email="qa+alpha@vendorclear.ai", phone="000-000-0005",
         city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-85), wc_expiry=d(-106), diversity_types=None,
         notes="Health Grade test vendor — expected grade F.",
         category=VendorCategory.CONSTRUCTION, vendor_type=VendorType.SUBCONTRACTOR,
         business_unit="Field Operations", region="Southwest",
         insurance_provider="Liberty Mutual", assigned_analyst_id="__ANALYST_1__"),
]


# ─── Documents for health grade test set ─────────────────────────────────────
HEALTH_GRADE_TEST_DOCS = {
    "Apex Construction Services":    ["Apex_COI.pdf", "Apex_Diversity_Certificate.pdf"],
    "GreenTech Solutions":           ["GreenTech_COI.pdf", "GreenTech_Diversity_Certificate.pdf"],
    "Metro Electrical Contractors":  ["Metro_COI.pdf", "Metro_Diversity_Certificate.pdf"],
    "Sunrise Logistics":             ["Sunrise_COI.pdf", "Sunrise_Diversity_Certificate.pdf"],
    "Alpha Industrial Works":        ["Alpha_COI.pdf", "Alpha_Diversity_Certificate.pdf"],
}


# ─── Sample findings for the analytics violations chart ───────────────────────
SAMPLE_FINDINGS = {
    "Metro Electrical Contractors": [
        ("GL_LIMIT_BELOW_POLICY_MIN", FindingSeverity.MEDIUM,
         "General liability limit is below the $3M minimum required for the Electrical policy."),
    ],
    "Sunrise Logistics": [
        ("WC_EXPIRING_SOON", FindingSeverity.HIGH,
         "Workers compensation coverage expires within the policy warning window."),
        ("MISSING_ADDITIONAL_INSURED", FindingSeverity.MEDIUM,
         "Certificate does not list the client as an additional insured."),
    ],
    "Alpha Industrial Works": [
        ("GL_EXPIRED", FindingSeverity.CRITICAL,
         "General liability coverage has already expired."),
        ("MISSING_ADDITIONAL_INSURED", FindingSeverity.HIGH,
         "Certificate does not list the client as an additional insured."),
    ],
    "Ironclad Line Services": [
        ("GL_EXPIRED", FindingSeverity.CRITICAL,
         "GL policy expired 30 days ago. Field contractor access suspended."),
    ],
    "Meridian Uniform Supply": [
        ("GL_EXPIRED", FindingSeverity.CRITICAL,
         "General liability coverage expired 14 days ago."),
        ("WC_EXPIRED", FindingSeverity.CRITICAL,
         "Workers compensation coverage expired 5 days ago."),
    ],
    "Voltage Components LLC": [
        ("GL_EXPIRING_SOON", FindingSeverity.HIGH,
         "GL certificate expires in 18 days — renewal urgently required."),
    ],
    "Summit Vegetation Management": [
        ("GL_EXPIRING_SOON", FindingSeverity.MEDIUM,
         "Both GL and WC expire in 25 days — schedule renewal."),
    ],
}


async def _ensure_schema_migration(conn):
    """Ensure Phase 2 columns exist in SQLite (idempotent)."""
    migrations = [
        "ALTER TABLE analyses ADD COLUMN field_confidences TEXT",
        "ALTER TABLE documents ADD COLUMN file_hash TEXT",
        "ALTER TABLE documents ADD COLUMN classification_confidence REAL",
        "ALTER TABLE documents ADD COLUMN classification_reasoning TEXT",
    ]
    for stmt in migrations:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                raise


async def seed():
    # Create tables + migrate schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_schema_migration(conn)

    async with AsyncSessionLocal() as db:
        # ── Version configs (Laasya's config service) ─────────────────────────
        try:
            from app.services.config_service import ConfigService
            await ConfigService(db).ensure_seeded()
            print("✓ Version configs seeded.")
            v1_cfg = await ConfigService(db).get_config(1)
            v2_cfg = await ConfigService(db).get_config(2)
        except Exception as e:
            print(f"  (Config service unavailable — skipping version config: {e})")
            v1_cfg = v2_cfg = None

        # ── Admin user ────────────────────────────────────────────────────────
        existing = await db.execute(select(User).where(User.email == "admin@vendorclear.com"))
        demo_user = existing.scalar_one_or_none()
        if not demo_user:
            # Also check the old email from previous sessions
            existing2 = await db.execute(select(User).where(User.email == "demo@vendorclear.ai"))
            demo_user = existing2.scalar_one_or_none()

        if not demo_user:
            demo_user = User(
                email="admin@vendorclear.com",
                full_name="Admin User (Hruthi)",
                hashed_password=hash_password("admin123"),
                is_admin=True,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(demo_user)
            await db.flush()
            print("✓ Created admin: admin@vendorclear.com / admin123")
        else:
            # Ensure it's admin
            demo_user.email = "admin@vendorclear.com"
            demo_user.hashed_password = hash_password("admin123")
            demo_user.role = UserRole.ADMIN
            demo_user.is_admin = True
            db.add(demo_user)
            await db.flush()
            print("✓ Admin user updated: admin@vendorclear.com / admin123")

        # ── Analyst users (team members) ──────────────────────────────────────
        async def get_or_create_user(email, full_name, role, password="DemoPass123"):
            existing_u = await db.execute(select(User).where(User.email == email))
            u = existing_u.scalar_one_or_none()
            if not u:
                u = User(
                    email=email, full_name=full_name,
                    hashed_password=hash_password(password),
                    is_admin=(role == UserRole.ADMIN),
                    role=role,
                    is_active=True,
                )
                db.add(u)
                await db.flush()
                print(f"✓ Created {role.value}: {email} / {password}")
            return u

        analyst1 = await get_or_create_user("nirupama@vendorclear.ai", "Nirupama (Analytics)", UserRole.ANALYST)
        analyst2 = await get_or_create_user("hruthi@vendorclear.ai", "Hruthi (OCR/Upload)", UserRole.ANALYST)
        analyst_ids = {"__ANALYST_1__": analyst1.id, "__ANALYST_2__": analyst2.id}

        await get_or_create_user("vendor.demo@vendorclear.ai", "Demo Vendor User", UserRole.VENDOR)
        await get_or_create_user("auditor.demo@vendorclear.ai", "Demo Auditor User", UserRole.AUDITOR)

        # ── Vendors ───────────────────────────────────────────────────────────
        created = 0
        for i, v in enumerate(VENDORS):
            existing_v = await db.execute(select(Vendor).where(Vendor.name == v["name"]))
            vendor = existing_v.scalar_one_or_none()
            if vendor:
                continue

            v = dict(v)
            # Resolve analyst placeholder → real ID
            if v.get("assigned_analyst_id") in analyst_ids:
                v["assigned_analyst_id"] = analyst_ids[v["assigned_analyst_id"]]
            else:
                v.pop("assigned_analyst_id", None)

            # Alternate version configs
            version = 1 if i % 2 == 0 else 2
            effective_cfg = {}
            if v1_cfg and v2_cfg:
                effective_cfg = dict(v1_cfg) if version == 1 else dict(v2_cfg)

            vendor = Vendor(
                **v,
                created_by_id=demo_user.id,
                assigned_version=version,
                effective_config=effective_cfg if effective_cfg else None,
                compliance_score=None,
            )
            db.add(vendor)
            await db.flush()
            created += 1

            # ── Documents + analyses for health grade test vendors ─────────────
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
                    file_hash=None,
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
                    file_hash=None,
                ))
                await db.flush()

            # ── Findings → Analysis → Compliance score ────────────────────────
            findings_for_vendor = SAMPLE_FINDINGS.get(v["name"])
            if findings_for_vendor and coi_doc is not None:
                analysis_status = (
                    AnalysisStatus.NON_COMPLIANT if vendor.status == VendorStatus.NON_COMPLIANT
                    else AnalysisStatus.NEEDS_REVIEW
                )
                analysis = Analysis(
                    document_id=coi_doc.id,
                    confidence_score=0.92,
                    field_confidences=None,
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
                await db.flush()

                # Compute and attach compliance score
                try:
                    from app.services.compliance_service import ComplianceService
                    score_data = await ComplianceService(db).compute_vendor_score(vendor.id)
                    vendor.compliance_score = score_data.get("total_score")
                    db.add(vendor)
                    await db.flush()
                except Exception as e:
                    print(f"  (Score compute skipped for {v['name']}: {e})")

        await db.commit()
        print(f"\n✓ Seeded {created} vendors ({len(VENDORS) - created} already existed).")
        print("\n─── Demo Logins ─────────────────────────────────────────────")
        print("  Admin:    admin@vendorclear.com    / admin123")
        print("  Analyst:  hruthi@vendorclear.ai   / DemoPass123")
        print("  Analyst:  nirupama@vendorclear.ai  / DemoPass123")
        print("  Vendor:   vendor.demo@vendorclear.ai / DemoPass123")
        print("  Auditor:  auditor.demo@vendorclear.ai / DemoPass123")
        print("────────────────────────────────────────────────────────────")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
