        created = 0
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        v1_cfg = await svc.get_config(1)
        v2_cfg = await svc.get_config(2)
        for i, v in enumerate(VENDORS):
            existing_v = await db.execute(select(Vendor).where(Vendor.name == v["name"]))
            vendor = existing_v.scalar_one_or_none()
            if vendor:
                continue
            v = dict(v)
            if v.get("assigned_analyst_id") in analyst_ids:
                v["assigned_analyst_id"] = analyst_ids[v["assigned_analyst_id"]]
            
            # Alternate demo vendors across versions so both are represented,
            # snapshotting the matching config onto each (Option A).
            version = 1 if i % 2 == 0 else 2
            cfg = v1_cfg if version == 1 else v2_cfg
            
            vendor = Vendor(
                **v, 
                created_by_id=demo_user.id,
                assigned_version=version, 
                effective_config=dict(cfg),
            )
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

        # Demo VENDOR user linked to the first vendor, to demonstrate the read-only vendor role.
        vend_existing = await db.execute(select(User).where(User.email == "vendor@vendorclear.ai"))
        if not vend_existing.scalar_one_or_none():
            first_vendor = (await db.execute(select(Vendor).limit(1))).scalar_one_or_none()
            if first_vendor:
                db.add(User(
                    email="vendor@vendorclear.ai",
                    full_name="Demo Vendor",
                    hashed_password=hash_password("VendorPass123"),
                    is_admin=False,
                    role=UserRole.VENDOR,
                    vendor_id=first_vendor.id,
                ))
                print("Created demo VENDOR: vendor@vendorclear.ai / VendorPass123")

        # Demo users for the remaining roles (Module 4/5 demonstration)
        for email, name, role_val in [
            ("analyst@vendorclear.ai", "Demo Analyst", UserRole.ANALYST),
            ("auditor@vendorclear.ai", "Demo Auditor", UserRole.AUDITOR),
        ]:
            exists = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not exists:
                db.add(User(
                    email=email, full_name=name,
                    hashed_password=hash_password("DemoPass123"),
                    is_admin=False, role=role_val,
                ))
                print(f"Created demo {role_val.value}: {email} / DemoPass123")

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
