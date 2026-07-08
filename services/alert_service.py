from sqlalchemy.orm import Session

from app.models.alert import Alert


class AlertService:

    @staticmethod
    def create_alert(
        db: Session,
        message: str,
        severity: str
    ):
        alert = Alert(
            message=message,
            severity=severity,
            status="Pending"
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        return alert

    @staticmethod
    def get_all_alerts(db: Session):
        return db.query(Alert).all()

    @staticmethod
    def resolve_alert(
        db: Session,
        alert_id: int
    ):
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if alert:
            alert.status = "Resolved"
            db.commit()
            db.refresh(alert)

        return alert
