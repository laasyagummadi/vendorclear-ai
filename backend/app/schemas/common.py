# ─────────────────────────────────────────────────────────────
#  app/schemas/common.py  —  Shared Pydantic response models
# ─────────────────────────────────────────────────────────────
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope."""
    success: bool = True
    message: str = "OK"
    data: Optional[T] = None


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    success: bool = False
    error: str
    details: Optional[list[ErrorDetail]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list envelope."""
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
