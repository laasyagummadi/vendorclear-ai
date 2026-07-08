from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    message: str
    severity: str
    status: str = "Pending"


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: str


class AlertResponse(AlertBase):
    id: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)