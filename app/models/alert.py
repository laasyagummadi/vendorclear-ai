from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    message = Column(String(500), nullable=False)

    severity = Column(String(50), nullable=False)

    status = Column(String(50), default="Pending")

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
