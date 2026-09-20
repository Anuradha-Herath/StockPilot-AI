from typing import Annotated
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

# Common DB Session Dependency
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.size = size


PaginationDep = Annotated[PaginationParams, Depends()]
