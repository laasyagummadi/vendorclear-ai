# ─────────────────────────────────────────────────────────────
#  app/controllers/document_controller.py  —  Upload pipeline (Hruthi)
# ─────────────────────────────────────────────────────────────
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.document import Document, DocumentType, DocumentStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.models.finding import Finding, FindingSeverity
from app.models.vendor import Vendor, VendorStatus, RiskTier
from app.services import file_storage_service, ocr_service, gemini_service
from app.repositories.document_repository import DocumentRepository


class DocumentController:
    """Orchestrates the 11-step document processing pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_and_analyze(
        self, file: UploadFile, vendor_id: str, doc_type_hint: str = "AUTO"
    ) -> Analysis:
        # 1. Verify vendor exists
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor {vendor_id} not found.",
            )

        # 1b. Resolve the vendor's effective (version-specific) config.
        # These thresholds drive the compliance rules below, so two vendors
        # on different versions can be judged against different requirements.
        from app.services.config_service import ConfigService
        from app.config_defaults import VERSION_1_DEFAULTS
        cfg = await ConfigService(self.db).get_effective_config(vendor)
        required_gl = cfg.get("required_gl_limit_usd", VERSION_1_DEFAULTS["required_gl_limit_usd"])
        min_ownership = cfg.get("min_ownership_percent", VERSION_1_DEFAULTS["min_ownership_percent"])
        min_confidence = cfg.get("min_confidence_score", VERSION_1_DEFAULTS["min_confidence_score"])
        require_addl_insured = cfg.get("require_additional_insured", VERSION_1_DEFAULTS["require_additional_insured"])

        # 2. Save file to disk
        file_path, file_size = await file_storage_service.save_upload(file)

        # 3. Create Document record (status=PROCESSING)
        document = Document(
            vendor_id=vendor_id,
            filename=file.filename,
            file_path=file_path,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            document_type=DocumentType.UNKNOWN,
            status=DocumentStatus.PROCESSING,
        )
        await DocumentRepository.create_document(self.db, document)
        await self.db.commit()

        # 4. OCR — extract raw text
        raw_text = ""
        try:
            raw_text = ocr_service.extract_text(file_path)
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")

        # 5. Detect document type
        resolved_type = DocumentType.UNKNOWN
        hint = doc_type_hint.upper()
        if hint == "COI":
            resolved_type = DocumentType.COI
        elif hint == "DIVERSITY_CERT":
            resolved_type = DocumentType.DIVERSITY_CERT
        else:
            tl = raw_text.lower()
            if any(k in tl for k in ["certificate of liability", "insured", "insurer", "coi"]):
                resolved_type = DocumentType.COI
            elif any(k in tl for k in ["diversity", "minority", "mbe", "wbe", "dbe", "ownership"]):
                resolved_type = DocumentType.DIVERSITY_CERT

        document.document_type = resolved_type
        self.db.add(document)

        # 6. Gemini structured extraction
        extracted: dict = {}
        confidence = 0.0
        try:
            if resolved_type == DocumentType.COI:
                extracted = await gemini_service.extract_coi(raw_text)
            elif resolved_type == DocumentType.DIVERSITY_CERT:
                extracted = await gemini_service.extract_diversity(raw_text)
            confidence = extracted.get("confidence_score", 0.0)
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")

        # 7. Evaluate compliance rules → generate Findings
        findings: list[Finding] = []
        now_date = datetime.utcnow().date()

        if resolved_type == DocumentType.COI:
            expiry_str = extracted.get("expiry_date")
            if not expiry_str:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="COI is missing an expiration date.",
                ))
            else:
                try:
                    exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if exp < now_date:
                        findings.append(Finding(
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"COI expired on {expiry_str}.",
                        ))
                except ValueError:
                    findings.append(Finding(
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"Expiry date '{expiry_str}' is not in YYYY-MM-DD format.",
                    ))

            gl = extracted.get("general_liability_limit_usd")
            if gl is None:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_GL_LIMIT",
                    message="General liability coverage limit not found.",
                ))
            elif gl < required_gl:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_GL_LIMIT",
                    message=f"GL limit ${gl:,.2f} is below the required ${required_gl:,.0f}.",
                ))

        elif resolved_type == DocumentType.DIVERSITY_CERT:
            expiry_str = extracted.get("expiry_date")
            if not expiry_str:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="Diversity certificate is missing an expiration date.",
                ))
            else:
                try:
                    exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if exp < now_date:
                        findings.append(Finding(
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"Diversity certificate expired on {expiry_str}.",
                        ))
                except ValueError:
                    findings.append(Finding(
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"Expiry date '{expiry_str}' is not in YYYY-MM-DD format.",
                    ))

            own = extracted.get("ownership_pct")
            if own is None:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_OWNERSHIP_PERCENT",
                    message="Diverse ownership percentage could not be determined.",
                ))
            elif own < min_ownership:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_OWNERSHIP_PERCENT",
                    message=f"Ownership {own}% is below the required {min_ownership}%.",
                ))

        # Global: low-confidence warning
        if confidence < min_confidence:
            findings.append(Finding(
                severity=FindingSeverity.MEDIUM,
                rule_code="LOW_CONFIDENCE",
                message=f"Extraction confidence {confidence:.2f} is below threshold {min_confidence:.2f}.",
            ))

        # 8. Determine verdict
        critical = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        if critical > 0:
            verdict = AnalysisStatus.NON_COMPLIANT
        elif high > 0 or confidence < 0.7:
            verdict = AnalysisStatus.NEEDS_REVIEW
        else:
            verdict = AnalysisStatus.COMPLIANT

        # 9. Create Analysis record
        analysis = Analysis(
            document_id=document.id,
            raw_text=raw_text,
            extracted_fields=extracted,
            confidence_score=confidence,
            status=verdict,
            insured_name=extracted.get("insured_name"),
            insurer_name=extracted.get("insurer_name"),
            policy_number=extracted.get("policy_number"),
            coverage_type=extracted.get("coverage_type"),
            general_liability_limit_usd=extracted.get("general_liability_limit_usd"),
            workers_comp_limit_usd=extracted.get("workers_comp_limit_usd"),
            auto_liability_limit_usd=extracted.get("auto_liability_limit_usd"),
            effective_date=extracted.get("effective_date"),
            expiry_date=extracted.get("expiry_date"),
            additional_insured=extracted.get("additional_insured", False),
            certificate_holder=extracted.get("certificate_holder"),
            cert_body=extracted.get("cert_body"),
            cert_type=extracted.get("cert_type"),
            cert_number=extracted.get("cert_number"),
            ownership_pct=extracted.get("ownership_pct"),
        )
        for f in findings:
            analysis.findings.append(f)
        await DocumentRepository.create_analysis(self.db, analysis)

        # 10. Mark document as PROCESSED
        document.status = DocumentStatus.PROCESSED
        self.db.add(document)

        # 11. Sync vendor status / risk / insurance dates
        if verdict == AnalysisStatus.COMPLIANT:
            vendor.status = VendorStatus.COMPLIANT
            vendor.risk_tier = RiskTier.LOW
        elif verdict == AnalysisStatus.NEEDS_REVIEW:
            vendor.status = VendorStatus.NEEDS_REVIEW
            vendor.risk_tier = RiskTier.MEDIUM
        else:
            vendor.status = VendorStatus.NON_COMPLIANT
            vendor.risk_tier = RiskTier.HIGH

        if resolved_type == DocumentType.COI:
            vendor.gl_expiry = extracted.get("expiry_date")
            wc_exp = extracted.get("workers_comp_expiry_date")
            if wc_exp:
                vendor.wc_expiry = wc_exp
            elif extracted.get("workers_comp_limit_usd"):
                vendor.wc_expiry = extracted.get("expiry_date")

        # Auto-fill vendor profile from whatever the document yielded.
        # IMPORTANT: only populate fields that are currently empty, so a
        # human's manual edits are never overwritten by a later upload.
        def _fill(attr, value):
            if value and not getattr(vendor, attr, None):
                setattr(vendor, attr, value)

        _fill("contact_name", extracted.get("contact_name"))
        _fill("email", extracted.get("email"))
        _fill("phone", extracted.get("phone"))
        _fill("address", extracted.get("address"))
        _fill("city", extracted.get("city"))
        _fill("state", extracted.get("state"))
        _fill("zip_code", extracted.get("zip_code"))

        # If the vendor was auto-created with a placeholder name, upgrade it
        # to the insured/certified business name from the document.
        insured = extracted.get("insured_name")
        if insured and (not vendor.name or vendor.name.strip().lower() in {"", "new vendor", "untitled"}):
            vendor.name = insured

        # Track diversity certification type on the vendor.
        cert_type = extracted.get("cert_type")
        if cert_type:
            existing = list(vendor.diversity_types or [])
            if cert_type not in existing:
                existing.append(cert_type)
                vendor.diversity_types = existing

        self.db.add(vendor)
        await self.db.commit()

        # Return with eagerly-loaded findings
        db_analysis = await DocumentRepository.get_analysis(self.db, analysis.id)
        return db_analysis
