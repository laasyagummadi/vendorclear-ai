from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import AlertCreate


class AlertRepository:

    @staticmethod
    def create(db: Session, alert: AlertCreate):
        db_alert = Alert(**alert.model_dump())

        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)

        return db_alert

    @staticmethod
    def get_all(db: Session):
        return db.query(Alert).all()

    @staticmethod
    def get_by_id(db: Session, alert_id: int):
        return db.query(Alert).filter(Alert.id == alert_id).first()

    @staticmethod
    def update_status(db: Session, db_alert: Alert, status: str):
        db_alert.status = status

        db.commit()
        db.refresh(db_alert)

        return db_alert

    @staticmethod
    def delete(db: Session, db_alert: Alert):
        db.delete(db_alert)
        db.commit()
