from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.services.alert_service import AlertService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.get("/")
def get_all_alerts(
    db: Session = Depends(get_sync_db)
):
    return AlertService.get_all_alerts(db)


@router.put("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_sync_db)
):
    alert = AlertService.resolve_alert(db, alert_id)

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    return {
        "message": "Alert resolved successfully",
        "alert": alert
    }
