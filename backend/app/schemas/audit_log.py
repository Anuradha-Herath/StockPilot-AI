from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from app.db.models.audit_log import ActorType


class AuditLogResponse(BaseModel):
    id: int
    actor_type: ActorType
    actor_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    payload_before: Optional[dict[str, Any]] = None
    payload_after: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
