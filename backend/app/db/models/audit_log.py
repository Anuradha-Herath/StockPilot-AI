import enum
from typing import Any
from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, PrimaryKeyMixin, utc_now


class ActorType(str, enum.Enum):
    AI_AGENT = "AI_AGENT"
    USER = "USER"
    SYSTEM = "SYSTEM"


class AuditLog(Base, PrimaryKeyMixin):
    __tablename__ = "audit_logs"

    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type_enum", native_enum=False),
        nullable=False,
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User ID or Agent identifier/thread_id",
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_before: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    payload_after: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_action_time", "action", "timestamp"),
    )
