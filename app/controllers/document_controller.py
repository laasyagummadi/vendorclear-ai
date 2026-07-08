import os
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
    """Orchestrates document processing, text extraction, Gemini AI extraction, and compliance rules evaluation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_and_analyze(
        self, file: UploadFile, vendor_id: str, doc_type_hint: str = "AUTO"
    ) -> Analysis:
        # 1. Fetch vendor to verify existence
        vendor_result = await self.db.get(Vendor, vendor_id)
        if not vendor_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor with ID {vendor_id} not found."
            )

        # 2. Save document to disk
        file_path, file_size = await file_storage_service.save_upload(file)

        # 3. Create Document DB record
        document = Document(
            vendor_id=vendor_id,
            filename=file.filename,
            file_path=file_path,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            document_type=DocumentType.UNKNOWN,
            status=DocumentStatus.PROCESSING
        )
        await DocumentRepository.create_document(self.db, document)
        await self.db.commit()

        # 4. Extract text from file (OCR)
        raw_text = ""
        try:
            raw_text = ocr_service.extract_text(file_path)
        except Exception as e:
            logger.error(f"OCR service failed: {str(e)}")

        # 5. Resolve Document Type
        resolved_type = DocumentType.UNKNOWN
        hint_upper = doc_type_hint.upper()
        
        if hint_upper == "COI":
            resolved_type = DocumentType.COI
        elif hint_upper == "DIVERSITY_CERT":
            resolved_type = DocumentType.DIVERSITY_CERT
        else:
            # AUTO detection logic based on keyword scanning
            text_lower = raw_text.lower()
            if any(k in text_lower for k in ["certificate of liability", "insured", "insurer", "coi"]):
                resolved_type = DocumentType.COI
            elif any(k in text_lower for k in ["diversity", "minority", "mbe", "wbe", "dbe", "ownership"]):
                resolved_type = DocumentType.DIVERSITY_CERT

        document.document_type = resolved_type
        self.db.add(document)

        # 6. Extract fields using Gemini structured extraction
        extracted_data = {}
        confidence = 0.0
        try:
            if resolved_type == DocumentType.COI:
                extracted_data = await gemini_service.extract_coi(raw_text)
            elif resolved_type == DocumentType.DIVERSITY_CERT:
                extracted_data = await gemini_service.extract_diversity(raw_text)
            
            confidence = extracted_data.get("confidence_score", 0.0)
        except Exception as e:
            logger.error(f"Gemini service extraction failed: {str(e)}")

        # 7. Evaluate Compliance Rules and Create Findings
        findings_to_add = []
        now_date = datetime.utcnow().date()

        # ── Rules for COI ──────────────────────────────────────────
        if resolved_type == DocumentType.COI:
            # Check Expiry
            expiry_str = extracted_data.get("expiry_date")
            if not expiry_str:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="The Certificate of Insurance is missing an expiration date."
                ))
            else:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if expiry_date < now_date:
                        findings_to_add.append(Finding(
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"The Certificate of Insurance expired on {expiry_str}."
                        ))
                except ValueError:
                    findings_to_add.append(Finding(
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"The expiration date format '{expiry_str}' is invalid. Must be YYYY-MM-DD."
                    ))

            # Check General Liability Limit (Require min 1,000,000 USD)
            gl_limit = extracted_data.get("general_liability_limit_usd")
            if gl_limit is None:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_GL_LIMIT",
                    message="General liability coverage limit is missing or could not be found."
                ))
            elif gl_limit < 1000000:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_GL_LIMIT",
                    message=f"General liability coverage limit (${gl_limit:,.2f}) is below the required $1,000,000.00."
                ))

        # ── Rules for Diversity Certificate ─────────────────────────
        elif resolved_type == DocumentType.DIVERSITY_CERT:
            # Check Expiry
            expiry_str = extracted_data.get("expiry_date")
            if not expiry_str:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_EXPIRY_DATE",
                    message="The diversity certification is missing an expiration date."
                ))
            else:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    if expiry_date < now_date:
                        findings_to_add.append(Finding(
                            severity=FindingSeverity.CRITICAL,
                            rule_code="DOCUMENT_EXPIRED",
                            message=f"The diversity certification expired on {expiry_str}."
                        ))
                except ValueError:
                    findings_to_add.append(Finding(
                        severity=FindingSeverity.HIGH,
                        rule_code="INVALID_EXPIRY_DATE",
                        message=f"The expiration date format '{expiry_str}' is invalid. Must be YYYY-MM-DD."
                    ))

            # Check Ownership Percentage (Require min 51.0%)
            ownership = extracted_data.get("ownership_pct")
            if ownership is None:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="MISSING_OWNERSHIP_PERCENT",
                    message="Diverse ownership percentage is missing or could not be found."
                ))
            elif ownership < 51.0:
                findings_to_add.append(Finding(
                    severity=FindingSeverity.HIGH,
                    rule_code="LOW_OWNERSHIP_PERCENT",
                    message=f"Diverse ownership percentage ({ownership}%) is below the required 51.0%."
                ))

        # ── Global Rules: Low Confidence Check ─────────────────────
        if confidence < 0.7:
            findings_to_add.append(Finding(
                severity=FindingSeverity.MEDIUM,
                rule_code="LOW_CONFIDENCE",
                message=f"The extraction confidence score ({confidence:.2f}) is below the required threshold of 0.7."
            ))

        # 8. Determine Analysis Status Verdict
        critical_count = sum(1 for f in findings_to_add if f.severity == FindingSeverity.CRITICAL)
        high_count = sum(1 for f in findings_to_add if f.severity == FindingSeverity.HIGH)
        
        if critical_count > 0:
            status_verdict = AnalysisStatus.NON_COMPLIANT
        elif high_count > 0 or confidence < 0.7:
            status_verdict = AnalysisStatus.NEEDS_REVIEW
        else:
            status_verdict = AnalysisStatus.COMPLIANT

        # 9. Create and save Analysis record
        analysis = Analysis(
            document_id=document.id,
            raw_text=raw_text,
            extracted_fields=extracted_data,
            confidence_score=confidence,
            status=status_verdict,
            
            # Map COI extracted fields
            insured_name=extracted_data.get("insured_name"),
            insurer_name=extracted_data.get("insurer_name"),
            policy_number=extracted_data.get("policy_number"),
            coverage_type=extracted_data.get("coverage_type"),
            general_liability_limit_usd=extracted_data.get("general_liability_limit_usd"),
            workers_comp_limit_usd=extracted_data.get("workers_comp_limit_usd"),
            auto_liability_limit_usd=extracted_data.get("auto_liability_limit_usd"),
            effective_date=extracted_data.get("effective_date"),
            expiry_date=extracted_data.get("expiry_date"),
            additional_insured=extracted_data.get("additional_insured", False),
            certificate_holder=extracted_data.get("certificate_holder"),

            # Map Diversity extracted fields
            cert_body=extracted_data.get("cert_body"),
            cert_type=extracted_data.get("cert_type"),
            cert_number=extracted_data.get("cert_number"),
            ownership_pct=extracted_data.get("ownership_pct")
        )

        for finding in findings_to_add:
            analysis.findings.append(finding)

        await DocumentRepository.create_analysis(self.db, analysis)

        # 10. Update Document status to PROCESSED
        document.status = DocumentStatus.PROCESSED
        self.db.add(document)

        # 11. Sync Vendor's main compliance fields
        # - vendor.status matches analysis.status
        # - vendor.gl_expiry / vendor.wc_expiry matches respective expiration dates
        if status_verdict == AnalysisStatus.COMPLIANT:
            vendor_result.status = VendorStatus.COMPLIANT
            vendor_result.risk_tier = RiskTier.LOW
        elif status_verdict == AnalysisStatus.NEEDS_REVIEW:
            vendor_result.status = VendorStatus.NEEDS_REVIEW
            vendor_result.risk_tier = RiskTier.MEDIUM
        else:
            vendor_result.status = VendorStatus.NON_COMPLIANT
            vendor_result.risk_tier = RiskTier.HIGH

        if resolved_type == DocumentType.COI:
            vendor_result.gl_expiry = extracted_data.get("expiry_date")
            wc_limit = extracted_data.get("workers_comp_limit_usd")
            if wc_limit:
                vendor_result.wc_expiry = extracted_data.get("expiry_date")

        self.db.add(vendor_result)
        await self.db.commit()
        
        # Eager load relationships using the repository to prevent lazy loading issues during serialization
        db_analysis = await DocumentRepository.get_analysis(self.db, analysis.id)
        return db_analysis
