from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class Supplier(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "suppliers"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_time_days: Mapped[int] = mapped_column(default=3, nullable=False)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("4.50"),
        nullable=False,
        comment="Supplier rating from 1.00 to 5.00",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    supplier_products: Mapped[list["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    purchase_requests: Mapped[list["PurchaseRequest"]] = relationship(
        "PurchaseRequest",
        back_populates="supplier",
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="supplier",
    )

    __table_args__ = (
        CheckConstraint("lead_time_days >= 0", name="chk_supplier_lead_time_non_negative"),
        CheckConstraint("rating >= 1.00 AND rating <= 5.00", name="chk_supplier_rating_range"),
    )
