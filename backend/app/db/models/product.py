from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class Product(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="unit", nullable=False)  # kg, unit, liter, pack, box
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Selling price per unit",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    inventory: Mapped["InventoryLevel"] = relationship(
        "InventoryLevel",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    supplier_products: Mapped[list["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    request_items: Mapped[list["PurchaseRequestItem"]] = relationship(
        "PurchaseRequestItem",
        back_populates="product",
    )
    order_items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem",
        back_populates="product",
    )

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="chk_product_unit_price_positive"),
        Index("ix_products_category_name", "category", "name"),
    )
