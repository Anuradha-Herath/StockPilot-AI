import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin, utc_now


class ApprovalDecision(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


class ApprovalRecord(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approval_records"

    purchase_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    purchase_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    approver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[ApprovalDecision] = mapped_column(
        Enum(ApprovalDecision, name="approval_decision_enum", native_enum=False),
        default=ApprovalDecision.PENDING,
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    approver: Mapped["User"] = relationship("User", back_populates="approval_records")
    purchase_request: Mapped["PurchaseRequest"] = relationship("PurchaseRequest", back_populates="approval_records")
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="approval_records")
