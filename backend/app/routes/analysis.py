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


@router.get("/recent", response_model=list[AnalysisOut])
async def get_recent_analyses(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Return the most recent analysis results."""
    analyses = await DocumentRepository.get_recent_analyses(db, limit)
    out_list = []
    for a in analyses:
        out = AnalysisOut.model_validate(a)
        if a.document:
            out.vendor_id = a.document.vendor_id
        out_list.append(out)
    return out_list


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
