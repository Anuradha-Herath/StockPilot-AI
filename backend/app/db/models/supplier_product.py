from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class SupplierProduct(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "supplier_products"

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Wholesale purchase cost per unit from this supplier",
    )
    min_order_qty: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Minimum order quantity required by supplier",
    )
    lead_time_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Product-specific lead time override",
    )
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="supplier_products")
    product: Mapped["Product"] = relationship("Product", back_populates="supplier_products")

    __table_args__ = (
        UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),
        CheckConstraint("unit_cost > 0", name="chk_supplier_product_cost_positive"),
        CheckConstraint("min_order_qty >= 1", name="chk_supplier_product_moq_positive"),
    )
