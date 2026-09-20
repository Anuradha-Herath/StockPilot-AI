from typing import Generic, List, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(..., description="Total count of matching records")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Page size limit")
    pages: int = Field(..., description="Total available pages")


class StatusResponse(BaseModel):
    success: bool = True
    message: str


class HealthCheckResponse(BaseModel):
    status: str
    environment: str
    database: str
    version: str = "1.0.0"
