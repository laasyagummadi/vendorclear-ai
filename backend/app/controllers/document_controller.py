# ─────────────────────────────────────────────────────────────
#  app/controllers/document_controller.py  —  Upload pipeline (Hruthi)
#  Phase 2 upgrades:
#   - Module 2: Automatic document classification via Gemini
#   - Module 7: SHA-256 duplicate detection before storing
#   - Module 8: Per-field confidence stored to field_confidences
#   - Module 10: Edge case handling — corrupt, blank, password PDFs
#   - Better error messages for every failure point
# ─────────────────────────────────────────────────────────────
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.document import Document, DocumentType, DocumentStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.models.finding import Finding, FindingSeverity
from app.models.vendor import Vendor, VendorStatus, RiskTier
from app.services import file_storage_service, ocr_service, gemini_service
from app.services.compliance_service import ComplianceService
from app.repositories.document_repository import DocumentRepository

# Map Gemini classification doc_type strings to our DocumentType enum
_CLASSIFY_MAP = {
    "COI": DocumentType.COI,
    "DIVERSITY_CERT": DocumentType.DIVERSITY_CERT,
    "CONTRACT": DocumentType.UNKNOWN,
    "INVOICE": DocumentType.UNKNOWN,
    "SAFETY_CERT": DocumentType.UNKNOWN,
    "UNKNOWN": DocumentType.UNKNOWN,
}


class DocumentController:
    """Orchestrates the Phase 2 document processing pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_duplicate(self, vendor_id: str, file_hash: str) -> dict | None:
        """
        Module 7: Check if a document with this SHA-256 hash already exists
        for this vendor. Returns the existing document dict or None.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.vendor_id == vendor_id,
                Document.file_hash == file_hash,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {
                "duplicate": True,
                "existing_document_id": existing.id,
                "existing_filename": existing.filename,
                "uploaded_at": existing.created_at.isoformat(),
            }
        return None

    async def upload_and_analyze(
        self, file: UploadFile, vendor_id: str, doc_type_hint: str = "AUTO"
    ) -> Analysis:
        # ── 1. Verify vendor exists ───────────────────────────
        vendor = await self.db.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor {vendor_id} not found.",
            )

        # ── 1b. Resolve vendor effective config ───────────────
        from app.services.config_service import ConfigService
        from app.config_defaults import VERSION_1_DEFAULTS
        cfg = await ConfigService(self.db).get_effective_config(vendor)
        required_gl = cfg.get("required_gl_limit_usd", VERSION_1_DEFAULTS["required_gl_limit_usd"])
        min_ownership = cfg.get("min_ownership_percent", VERSION_1_DEFAULTS["min_ownership_percent"])
        min_confidence = cfg.get("min_confidence_score", VERSION_1_DEFAULTS["min_confidence_score"])
        require_addl_insured = cfg.get("require_additional_insured", VERSION_1_DEFAULTS["require_additional_insured"])

        # ── 2. Validate file before saving ────────────────────
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file was provided.")

        content_type = (file.content_type or "").lower()
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        allowed_exts = {"pdf", "png", "jpg", "jpeg", "tiff", "tif", "docx"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '.{ext}'. Accepted: PDF, PNG, JPG, JPEG, TIFF, DOCX.",
            )

        # ── 3. Read file bytes for hash (Module 7) ────────────
        file_bytes = await file.read()
        await file.seek(0)  # reset for file_storage_service.save_upload

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty (0 bytes).")

        file_hash = ocr_service.compute_bytes_hash(file_bytes)

        # ── 4. Save file to disk ──────────────────────────────
        file_path, file_size = await file_storage_service.save_upload(file)

        # ── 5. Create Document record (status=PROCESSING) ─────
        document = Document(
            vendor_id=vendor_id,
            filename=file.filename,
            file_path=file_path,
            file_size_bytes=file_size,
            mime_type=file.content_type or "application/octet-stream",
            document_type=DocumentType.UNKNOWN,
            status=DocumentStatus.PROCESSING,
            file_hash=file_hash,
        )
        await DocumentRepository.create_document(self.db, document)
        await self.db.commit()

        # ── 6. OCR — extract raw text (Module 9, 10) ─────────
        raw_text = ""
        ocr_error = None
        try:
            raw_text = ocr_service.extract_text(file_path)
        except ValueError as e:
            # Edge case handling: user-friendly error for known failure modes
            ocr_error = str(e)
            logger.warning(f"OCR rejected document {file.filename}: {ocr_error}")
            document.status = DocumentStatus.FAILED
            self.db.add(document)
            await self.db.commit()
            raise HTTPException(status_code=422, detail=ocr_error)
        except Exception as e:
            logger.error(f"Unexpected OCR error for {file_path}: {e}")
            # Don't abort — continue with empty text and let Gemini/mock handle it
            raw_text = ""

        # ── 7. Module 2: Automatic document classification ────
        resolved_type = DocumentType.UNKNOWN
        classification_confidence = None
        classification_reasoning = None
        hint = doc_type_hint.upper()

        if hint == "COI":
            resolved_type = DocumentType.COI
        elif hint == "DIVERSITY_CERT":
            resolved_type = DocumentType.DIVERSITY_CERT
        else:
            # AUTO: try Gemini classification first, then keyword fallback
            try:
                cls = await gemini_service.classify_document(raw_text)
                resolved_type = _CLASSIFY_MAP.get(cls["doc_type"], DocumentType.UNKNOWN)
                classification_confidence = cls.get("confidence")
                classification_reasoning = cls.get("reasoning")
                logger.info(
                    f"Auto-classified '{file.filename}' as {cls['doc_type']} "
                    f"(confidence={cls['confidence']:.2f}): {cls['reasoning']}"
                )
            except Exception as e:
                logger.warning(f"Classification failed, using keyword fallback: {e}")
                tl = raw_text.lower()
                if any(k in tl for k in ["certificate of liability", "insured", "insurer", "coi", "acord"]):
                    resolved_type = DocumentType.COI
                elif any(k in tl for k in ["diversity", "minority", "mbe", "wbe", "dbe", "ownership"]):
                    resolved_type = DocumentType.DIVERSITY_CERT

        document.document_type = resolved_type
        document.classification_confidence = classification_confidence
        document.classification_reasoning = classification_reasoning
        self.db.add(document)

        # ── 8. Gemini structured extraction ──────────────────
        extracted: dict = {}
        confidence = 0.0
        field_confidences: dict = {}
        try:
            if resolved_type == DocumentType.COI:
                extracted = await gemini_service.extract_coi(raw_text)
            elif resolved_type == DocumentType.DIVERSITY_CERT:
                extracted = await gemini_service.extract_diversity(raw_text)
            confidence = extracted.get("confidence_score", 0.0)
            field_confidences = extracted.get("field_confidences", {})
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")

        # ── 9. Evaluate compliance rules → generate Findings ──
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

        elif resolved_type == DocumentType.UNKNOWN:
            findings.append(Finding(
                severity=FindingSeverity.MEDIUM,
                rule_code="UNKNOWN_DOCUMENT_TYPE",
                message="Document type could not be determined. Please manually verify.",
            ))

        # Global: low-confidence warning
        if confidence < min_confidence and resolved_type != DocumentType.UNKNOWN:
            findings.append(Finding(
                severity=FindingSeverity.MEDIUM,
                rule_code="LOW_CONFIDENCE",
                message=f"Extraction confidence {confidence:.2f} is below threshold {min_confidence:.2f}.",
            ))

        # ── 10. Determine verdict ─────────────────────────────
        critical = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        if critical > 0:
            verdict = AnalysisStatus.NON_COMPLIANT
        elif high > 0 or confidence < 0.7:
            verdict = AnalysisStatus.NEEDS_REVIEW
        else:
            verdict = AnalysisStatus.COMPLIANT

        # ── 11. Create Analysis record ────────────────────────
        analysis = Analysis(
            document_id=document.id,
            raw_text=raw_text,
            extracted_fields=extracted,
            confidence_score=confidence,
            field_confidences=field_confidences,  # Module 8
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

        # ── 12. Mark document as PROCESSED ───────────────────
        document.status = DocumentStatus.PROCESSED
        self.db.add(document)

        # ── 13. Sync vendor status / risk / insurance dates ───
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

        insured = extracted.get("insured_name")
        if insured and (not vendor.name or vendor.name.strip().lower() in {"", "new vendor", "untitled"}):
            vendor.name = insured

        cert_type = extracted.get("cert_type")
        if cert_type:
            existing = list(vendor.diversity_types or [])
            if cert_type not in existing:
                existing.append(cert_type)
                vendor.diversity_types = existing

        self.db.add(vendor)

        # ── 14. Compute and persist compliance score ──────────
        await self.db.flush()
        score_data = await ComplianceService(self.db).compute_vendor_score(vendor.id)
        vendor.compliance_score = score_data.get("total_score")
        self.db.add(vendor)

        await self.db.commit()

        db_analysis = await DocumentRepository.get_analysis(self.db, analysis.id)
        return db_analysis

    async def update_and_re_evaluate(
        self, analysis_id: str, data: dict, user_id: str
    ) -> Analysis:
        # ── 1. Fetch analysis ─────────────────────────────────
        analysis = await self.db.get(Analysis, analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found.")

        document = await self.db.get(Document, analysis.document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        vendor = await self.db.get(Vendor, document.vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found.")

        # ── 2. Update analysis fields ─────────────────────────
        for k, v in data.items():
            if hasattr(analysis, k):
                setattr(analysis, k, v)

        # ── 3. Resolve vendor effective config ────────────────
        from app.services.config_service import ConfigService
        from app.config_defaults import VERSION_1_DEFAULTS
        cfg = await ConfigService(self.db).get_effective_config(vendor)
        required_gl = cfg.get("required_gl_limit_usd", VERSION_1_DEFAULTS["required_gl_limit_usd"])
        min_ownership = cfg.get("min_ownership_percent", VERSION_1_DEFAULTS["min_ownership_percent"])
        min_confidence = cfg.get("min_confidence_score", VERSION_1_DEFAULTS["min_confidence_score"])

        # ── 4. Clear old findings ─────────────────────────────
        from sqlalchemy import delete
        from app.models.finding import Finding
        await self.db.execute(delete(Finding).where(Finding.analysis_id == analysis.id))
        analysis.findings = []

        # ── 5. Evaluate compliance rules ──────────────────────
        findings = []
        now_date = datetime.utcnow().date()

        if document.document_type == DocumentType.COI:
            expiry_str = analysis.expiry_date
            if not expiry_str:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="COI is missing an expiration date.",
                ))
            else:
                try:
                    exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if exp < now_date:
                        findings.append(Finding(
                            analysis_id=analysis.id,
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"COI expired on {expiry_str}.",
                        ))
                except ValueError:
                    findings.append(Finding(
                        analysis_id=analysis.id,
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"Expiry date '{expiry_str}' is not in YYYY-MM-DD format.",
                    ))

            gl = analysis.general_liability_limit_usd
            if gl is None:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_GL_LIMIT",
                    message="General liability coverage limit not found.",
                ))
            elif gl < required_gl:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_GL_LIMIT",
                    message=f"GL limit ${gl:,.2f} is below the required ${required_gl:,.0f}.",
                ))

        elif document.document_type == DocumentType.DIVERSITY_CERT:
            expiry_str = analysis.expiry_date
            if not expiry_str:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="Diversity certificate is missing an expiration date.",
                ))
            else:
                try:
                    exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if exp < now_date:
                        findings.append(Finding(
                            analysis_id=analysis.id,
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"Diversity certificate expired on {expiry_str}.",
                        ))
                except ValueError:
                    findings.append(Finding(
                        analysis_id=analysis.id,
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"Expiry date '{expiry_str}' is not in YYYY-MM-DD format.",
                    ))

            own = analysis.ownership_pct
            if own is None:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_OWNERSHIP_PERCENT",
                    message="Diverse ownership percentage could not be determined.",
                ))
            elif own < min_ownership:
                findings.append(Finding(
                    analysis_id=analysis.id,
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_OWNERSHIP_PERCENT",
                    message=f"Ownership {own}% is below the required {min_ownership}%.",
                ))

        if analysis.confidence_score < min_confidence:
            findings.append(Finding(
                analysis_id=analysis.id,
                severity=FindingSeverity.MEDIUM,
                rule_code="LOW_CONFIDENCE",
                message=f"Extraction confidence {analysis.confidence_score:.2f} is below threshold {min_confidence:.2f}.",
            ))

        # ── 6. Determine verdict ──────────────────────────────
        critical = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        if critical > 0:
            verdict = AnalysisStatus.NON_COMPLIANT
        elif high > 0 or analysis.confidence_score < 0.7:
            verdict = AnalysisStatus.NEEDS_REVIEW
        else:
            verdict = AnalysisStatus.COMPLIANT

        analysis.status = verdict
        for f in findings:
            analysis.findings.append(f)
            self.db.add(f)

        self.db.add(analysis)

        # ── 7. Sync vendor status ─────────────────────────────
        if verdict == AnalysisStatus.COMPLIANT:
            vendor.status = VendorStatus.COMPLIANT
            vendor.risk_tier = RiskTier.LOW
        elif verdict == AnalysisStatus.NEEDS_REVIEW:
            vendor.status = VendorStatus.NEEDS_REVIEW
            vendor.risk_tier = RiskTier.MEDIUM
        else:
            vendor.status = VendorStatus.NON_COMPLIANT
            vendor.risk_tier = RiskTier.HIGH

        if document.document_type == DocumentType.COI:
            vendor.gl_expiry = analysis.expiry_date
            if analysis.workers_comp_limit_usd:
                vendor.wc_expiry = analysis.expiry_date

        self.db.add(vendor)

        # ── 8. Compute and persist compliance score ───────────
        await self.db.flush()
        score_data = await ComplianceService(self.db).compute_vendor_score(vendor.id)
        vendor.compliance_score = score_data.get("total_score")
        self.db.add(vendor)

        # ── 9. Log audit event ────────────────────────────────
        from app.services.audit_service import AuditService
        from app.models.audit import AuditAction
        audit_svc = AuditService(self.db)
        await audit_svc.log(
            user_id=user_id,
            action=AuditAction.VENDOR_UPDATED,
            target_type="vendor",
            target_id=vendor.id,
            details={"message": f"Document analysis {analysis_id} edited and compliance re-evaluated."},
        )

        await self.db.commit()

        db_analysis = await DocumentRepository.get_analysis(self.db, analysis.id)
        return db_analysis
