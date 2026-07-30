# ─────────────────────────────────────────────────────────────
#  app/routes/analysis.py  —  Analysis result endpoints
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user_id
from app.repositories.document_repository import DocumentRepository
from app.schemas.analysis import AnalysisOut

router = APIRouter(
    prefix="/analyses",
    tags=["analysis"],
)


def _to_out(analysis) -> AnalysisOut:
    out = AnalysisOut.model_validate(analysis)
    if analysis.document:
        out.vendor_id = analysis.document.vendor_id
    return out


@router.get("/recent", response_model=List[AnalysisOut])
async def get_recent_analyses(
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    """Most recent analyses across all documents (for the upload dashboard).
    NOTE: this route must be declared before /{analysis_id} so that the
    literal path 'recent' is not captured as an analysis id."""
    analyses = await DocumentRepository.get_recent_analyses(db, limit=limit)
    return [_to_out(a) for a in analyses]


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
    return _to_out(analysis)


from app.schemas.analysis import AnalysisUpdate
from app.controllers.document_controller import DocumentController

@router.put("/{analysis_id}", response_model=AnalysisOut)
async def update_analysis(
    analysis_id: str,
    data: AnalysisUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update analysis fields and trigger compliance re-evaluation."""
    ctrl = DocumentController(db)
    update_data = data.model_dump(exclude_unset=True)
    updated_analysis = await ctrl.update_and_re_evaluate(analysis_id, update_data, user_id)
    return _to_out(updated_analysis)
