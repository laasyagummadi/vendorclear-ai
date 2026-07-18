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
            
            # Multimodal fallback for type detection if local OCR returned empty text
            if resolved_type == DocumentType.UNKNOWN and not raw_text.strip():
                logger.info(f"Empty OCR text, trying Gemini multimodal type detection for {file_path}")
                detected = await gemini_service.detect_document_type(file_path)
                if detected == "COI":
                    resolved_type = DocumentType.COI
                elif detected == "DIVERSITY_CERT":
                    resolved_type = DocumentType.DIVERSITY_CERT

        document.document_type = resolved_type
        self.db.add(document)

        # 6. Gemini structured extraction
        extracted: dict = {}
        confidence = 0.0
        try:
            if resolved_type == DocumentType.COI:
                extracted = await gemini_service.extract_coi(raw_text, file_path)
            elif resolved_type == DocumentType.DIVERSITY_CERT:
                extracted = await gemini_service.extract_diversity(raw_text, file_path)
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
            elif gl < 1_000_000:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_GL_LIMIT",
                    message=f"GL limit ${gl:,.2f} is below the required $1,000,000.",
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
            elif own < 51.0:
                findings.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_OWNERSHIP_PERCENT",
                    message=f"Ownership {own}% is below the required 51%.",
                ))

        # Global: low-confidence warning
        if confidence < 0.7:
            findings.append(Finding(
                severity=FindingSeverity.MEDIUM,
                rule_code="LOW_CONFIDENCE",
                message=f"Extraction confidence {confidence:.2f} is below threshold 0.70.",
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
            if extracted.get("workers_comp_limit_usd"):
                vendor.wc_expiry = extracted.get("expiry_date")

        self.db.add(vendor)
        await self.db.commit()

        # Return with eagerly-loaded findings
        db_analysis = await DocumentRepository.get_analysis(self.db, analysis.id)
        return db_analysis
