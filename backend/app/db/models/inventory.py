from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, PrimaryKeyMixin, TimestampMixin


class InventoryLevel(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory_levels"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Stock reserved for pending customer checkouts or transfers",
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        comment="Threshold stock level that triggers replenishment alerts",
    )
    reorder_quantity: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
        comment="Standard batch quantity to order when replenishing",
    )
    max_stock: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Warehouse storage capacity ceiling for this SKU",
    )
    warehouse_location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Aisle/Shelf code e.g. AISLE-03-B2",
    )
    last_restocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory")

    @property
    def available_stock(self) -> int:
        return max(0, self.current_stock - self.reserved_stock)

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_point

    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="chk_inventory_current_stock_non_negative"),
        CheckConstraint("reserved_stock >= 0", name="chk_inventory_reserved_stock_non_negative"),
        CheckConstraint("reorder_point >= 0", name="chk_inventory_reorder_point_non_negative"),
        CheckConstraint("reorder_quantity >= 1", name="chk_inventory_reorder_qty_positive"),
        CheckConstraint("max_stock >= reorder_point", name="chk_inventory_max_gte_reorder"),
    )
