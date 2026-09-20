import math
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import ActorType, AuditLog
from app.schemas.audit_log import AuditLogResponse


class AuditService:
    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        actor_type: Optional[ActorType] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        size: int = 30,
    ) -> Tuple[List[AuditLogResponse], int]:
        """Lists audit log records in reverse chronological order."""
        query = select(AuditLog).order_by(AuditLog.timestamp.desc())
        count_query = select(func.count(AuditLog.id))

        if actor_type is not None:
            query = query.where(AuditLog.actor_type == actor_type)
            count_query = count_query.where(AuditLog.actor_type == actor_type)

        if action:
            query = query.where(AuditLog.action.ilike(f"%{action.strip()}%"))
            count_query = count_query.where(AuditLog.action.ilike(f"%{action.strip()}%"))

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
            count_query = count_query.where(AuditLog.entity_type == entity_type)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [AuditLogResponse.model_validate(log) for log in logs], total
