from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import DBSessionDep
from app.core.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def check_health(db: DBSessionDep):
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthCheckResponse(
        status="ok" if "healthy" in db_status else "degraded",
        environment=settings.ENVIRONMENT,
        database=db_status,
        version="1.0.0",
    )
