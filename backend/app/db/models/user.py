import enum
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    OPERATOR = "OPERATOR"
    AUDITOR = "AUDITOR"


class User(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.OPERATOR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    purchase_requests: Mapped[list["PurchaseRequest"]] = relationship(
        "PurchaseRequest", back_populates="requester", foreign_keys="PurchaseRequest.requester_id"
    )
    approved_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="approved_by", foreign_keys="PurchaseOrder.approved_by_id"
    )
    created_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="created_by", foreign_keys="PurchaseOrder.created_by_id"
    )
    approval_records: Mapped[list["ApprovalRecord"]] = relationship(
        "ApprovalRecord", back_populates="approver"
    )
