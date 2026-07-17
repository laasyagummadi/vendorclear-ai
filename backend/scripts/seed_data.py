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
from app.models.user import User
from app.models.vendor import Vendor, VendorStatus, RiskTier
from app.utils.security import hash_password


def d(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


VENDORS = [
    # ── Electronics ──────────────────────────────────────────
    dict(name="Circuit Dynamics Inc.", contact_name="Priya Raman", email="priya@circuitdynamics.com",
         phone="512-555-0142", city="Austin", state="TX", zip_code="78701",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(180), wc_expiry=d(200), diversity_types=["MBE"],
         notes="Primary supplier for grid sensor hardware."),
    dict(name="Voltage Components LLC", contact_name="Mark Delgado", email="mark@voltagecomponents.com",
         phone="619-555-0110", city="San Diego", state="CA", zip_code="92101",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(18), wc_expiry=d(90), diversity_types=None,
         notes="GL certificate expiring soon — follow up requested."),

    # ── Grocery / Food Service ───────────────────────────────
    dict(name="Harvest Point Foods", contact_name="Lena Cho", email="lena@harvestpointfoods.com",
         phone="303-555-0177", city="Denver", state="CO", zip_code="80202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(240), wc_expiry=d(210), diversity_types=["WBE"],
         notes="Cafeteria catering contract, renews annually."),

    # ── Fashion ───────────────────────────────────────────────
    dict(name="Meridian Uniform Supply", contact_name="Oscar Reyes", email="oscar@meridianuniforms.com",
         phone="214-555-0199", city="Dallas", state="TX", zip_code="75201",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-14), wc_expiry=d(-5), diversity_types=["HUBZone"],
         notes="Insurance lapsed — field crew uniforms on hold pending renewal."),

    # ── Furniture ─────────────────────────────────────────────
    dict(name="Redwood Office Furnishings", contact_name="Grace Lin", email="grace@redwoodoffice.com",
         phone="415-555-0133", city="San Francisco", state="CA", zip_code="94105",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(300), wc_expiry=d(300), diversity_types=None,
         notes="Office buildout vendor for regional facilities."),

    # ── Pharmacy / Medical Supply ────────────────────────────
    dict(name="ClearPath Medical Supply", contact_name="Dr. Sam Okafor", email="sam@clearpathmed.com",
         phone="404-555-0166", city="Atlanta", state="GA", zip_code="30303",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(45), wc_expiry=d(6), diversity_types=["MBE", "SBE"],
         notes="Workers comp expiring within a week — urgent renewal needed."),

    # ── Restaurants (on-site vending / crew catering) ───────
    dict(name="Blue Ridge Catering Co.", contact_name="Tasha Brooks", email="tasha@blueridgecatering.com",
         phone="828-555-0121", city="Asheville", state="NC", zip_code="28801",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(150), wc_expiry=d(150), diversity_types=["WBE", "DBE"],
         notes="Crew catering for field operations."),

    # ── Home Services / Field Contractors ────────────────────
    dict(name="Ironclad Line Services", contact_name="Bill Harrington", email="bill@ironcladline.com",
         phone="602-555-0155", city="Phoenix", state="AZ", zip_code="85003",
         status=VendorStatus.NON_COMPLIANT, risk_tier=RiskTier.HIGH,
         gl_expiry=d(-30), wc_expiry=d(120), diversity_types=None,
         notes="GL policy expired 30 days ago — high-risk field contractor, escalate."),
    dict(name="Summit Vegetation Management", contact_name="Renee Park", email="renee@summitveg.com",
         phone="503-555-0188", city="Portland", state="OR", zip_code="97201",
         status=VendorStatus.NEEDS_REVIEW, risk_tier=RiskTier.MEDIUM,
         gl_expiry=d(25), wc_expiry=d(25), diversity_types=["VOSB"],
         notes="Right-of-way clearing crew, renewal in progress."),

    # ── Local Shops / Small Business ──────────────────────────
    dict(name="Prairie Hardware & Supply", contact_name="Wendell Moss", email="wendell@prairiehardware.com",
         phone="316-555-0144", city="Wichita", state="KS", zip_code="67202",
         status=VendorStatus.COMPLIANT, risk_tier=RiskTier.LOW,
         gl_expiry=d(200), wc_expiry=d(200), diversity_types=["SBE"],
         notes="Local materials supplier, long-standing relationship."),
]


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
            )
            db.add(demo_user)
            await db.flush()
            print(f"Created demo user: demo@vendorclear.ai / DemoPass123")
        else:
            print("Demo user already exists, skipping.")

        created = 0
        for v in VENDORS:
            existing_v = await db.execute(select(Vendor).where(Vendor.name == v["name"]))
            if existing_v.scalar_one_or_none():
                continue
            db.add(Vendor(**v, created_by_id=demo_user.id))
            created += 1

        await db.commit()
        print(f"Seeded {created} vendors ({len(VENDORS) - created} already existed).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
