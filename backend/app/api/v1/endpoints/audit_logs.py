import math
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import DBSessionDep, PaginationDep
from app.db.models.audit_log import ActorType
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    db: DBSessionDep,
    pagination: PaginationDep,
    actor_type: Optional[ActorType] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
):
    """Retrieve system audit logs with optional filtering by actor type, action, and entity."""
    logs, total = await AuditService.list_audit_logs(
        db=db,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        page=pagination.page,
        size=pagination.size,
    )
    pages = math.ceil(total / pagination.size) if total > 0 else 1

    return PaginatedResponse[AuditLogResponse](
        items=logs,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )
