# ─────────────────────────────────────────────────────────────
#  app/routes/analysis.py  —  Analysis result endpoints
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.repositories.document_repository import DocumentRepository
from app.schemas.analysis import AnalysisOut

router = APIRouter(
    prefix="/analyses",
    tags=["analysis"],
)


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Return a single analysis result with all findings."""
    analysis = await DocumentRepository.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    out = AnalysisOut.model_validate(analysis)
    if analysis.document:
        out.vendor_id = analysis.document.vendor_id
    return out
