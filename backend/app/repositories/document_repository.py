# ─────────────────────────────────────────────────────────────
#  app/repositories/document_repository.py  —  Doc + Analysis CRUD (Hruthi)
# ─────────────────────────────────────────────────────────────
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.analysis import Analysis
from app.models.finding import Finding


class DocumentRepository:
    """Async CRUD for Document, Analysis, and Finding records."""

    # ── Document ──────────────────────────────────────────────

    @staticmethod
    async def create_document(db: AsyncSession, document: Document) -> Document:
        db.add(document)
        await db.flush()
        return document

    @staticmethod
    async def get_document(db: AsyncSession, document_id: str) -> Optional[Document]:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_vendor_documents(db: AsyncSession, vendor_id: str) -> List[Document]:
        result = await db.execute(
            select(Document).where(Document.vendor_id == vendor_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_document_status(
        db: AsyncSession, document_id: str, status: str
    ) -> Optional[Document]:
        doc = await DocumentRepository.get_document(db, document_id)
        if doc:
            doc.status = status
            db.add(doc)
            await db.flush()
        return doc

    # ── Analysis ──────────────────────────────────────────────

    @staticmethod
    async def create_analysis(db: AsyncSession, analysis: Analysis) -> Analysis:
        db.add(analysis)
        await db.flush()
        return analysis

    @staticmethod
    async def get_analysis(db: AsyncSession, analysis_id: str) -> Optional[Analysis]:
        result = await db.execute(
            select(Analysis)
            .where(Analysis.id == analysis_id)
            .options(selectinload(Analysis.findings), selectinload(Analysis.document))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_analyses_for_document(
        db: AsyncSession, document_id: str
    ) -> List[Analysis]:
        result = await db.execute(
            select(Analysis)
            .where(Analysis.document_id == document_id)
            .options(selectinload(Analysis.findings))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_analyses(db: AsyncSession, limit: int = 5) -> List[Analysis]:
        result = await db.execute(
            select(Analysis)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .options(selectinload(Analysis.findings), selectinload(Analysis.document))
        )
        return list(result.scalars().all())

    # ── Finding ───────────────────────────────────────────────

    @staticmethod
    async def get_findings_by_analysis(
        db: AsyncSession, analysis_id: str
    ) -> List[Finding]:
        result = await db.execute(
            select(Finding).where(Finding.analysis_id == analysis_id)
        )
        return list(result.scalars().all())
