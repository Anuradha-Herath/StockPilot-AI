import enum
from decimal import Decimal
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class PurchaseRequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED_TO_PO = "CONVERTED_TO_PO"
    CANCELLED = "CANCELLED"


class PriorityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PurchaseRequest(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_requests"

    request_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    requester_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User ID or NULL if generated automatically by AI Agent",
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[PurchaseRequestStatus] = mapped_column(
        Enum(PurchaseRequestStatus, name="purchase_request_status_enum", native_enum=False),
        default=PurchaseRequestStatus.DRAFT,
        nullable=False,
        index=True,
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel, name="priority_level_enum", native_enum=False),
        default=PriorityLevel.MEDIUM,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Relationships
    requester: Mapped["User"] = relationship("User", back_populates="purchase_requests", foreign_keys=[requester_id])
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="purchase_requests")
    items: Mapped[list["PurchaseRequestItem"]] = relationship(
        "PurchaseRequestItem",
        back_populates="purchase_request",
        cascade="all, delete-orphan",
    )
    approval_records: Mapped[list["ApprovalRecord"]] = relationship(
        "ApprovalRecord",
        back_populates="purchase_request",
    )

    __table_args__ = (
        CheckConstraint("total_estimated_cost >= 0", name="chk_request_total_cost_positive"),
    )


class PurchaseRequestItem(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_request_items"

    purchase_request_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    purchase_request: Mapped["PurchaseRequest"] = relationship("PurchaseRequest", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="request_items")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="chk_request_item_qty_positive"),
        CheckConstraint("estimated_unit_cost >= 0", name="chk_request_item_unit_cost_positive"),
        CheckConstraint("total_cost >= 0", name="chk_request_item_total_cost_positive"),
    )
