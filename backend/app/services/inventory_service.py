import enum
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.db.models.audit_log import ActorType, AuditLog
from app.db.models.inventory import InventoryLevel
from app.db.models.product import Product
from app.db.models.supplier import Supplier
from app.db.models.supplier_product import SupplierProduct
from app.schemas.inventory import (
    LowStockItemResponse,
    StockAdjustmentRequest,
    StockSummaryResponse,
)


class StockStatusFilter(str, enum.Enum):
    ALL = "ALL"
    HEALTHY = "HEALTHY"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class InventoryService:
    @staticmethod
    async def get_stock_summary(db: AsyncSession) -> StockSummaryResponse:
        """Calculate high-level inventory metrics."""
        prod_count = (await db.execute(select(func.count(Product.id)))).scalar_one()

        inv_query = select(
            func.count().filter(InventoryLevel.current_stock <= InventoryLevel.reorder_point).label("low_stock"),
            func.count().filter(InventoryLevel.current_stock == 0).label("out_of_stock"),
            func.count().filter(InventoryLevel.current_stock > InventoryLevel.reorder_point).label("healthy"),
        )
        inv_result = (await db.execute(inv_query)).one()
        low_stock_count = inv_result.low_stock or 0
        out_of_stock_count = inv_result.out_of_stock or 0
        healthy_count = inv_result.healthy or 0

        val_query = select(
            func.coalesce(func.sum(InventoryLevel.current_stock * Product.unit_price), Decimal("0.00"))
        ).join(Product, InventoryLevel.product_id == Product.id)
        total_valuation = (await db.execute(val_query)).scalar_one()

        return StockSummaryResponse(
            total_products=prod_count,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            healthy_stock_count=healthy_count,
            total_inventory_valuation=Decimal(str(total_valuation)),
        )

    @staticmethod
    async def lookup_inventory(
        db: AsyncSession,
        product_id: Optional[int] = None,
        sku: Optional[str] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        stock_status: StockStatusFilter = StockStatusFilter.ALL,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[dict], int]:
        """Lookup inventory records by SKU, product_id, name, category, and stock status."""
        query = (
            select(Product, InventoryLevel)
            .join(InventoryLevel, Product.id == InventoryLevel.product_id)
            .options(
                selectinload(Product.supplier_products).joinedload(SupplierProduct.supplier)
            )
        )

        if product_id is not None:
            query = query.where(Product.id == product_id)

        if sku is not None:
            query = query.where(Product.sku.ilike(sku.strip()))

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                (Product.name.ilike(search_pattern))
                | (Product.sku.ilike(search_pattern))
                | (Product.category.ilike(search_pattern))
            )

        if category:
            query = query.where(Product.category.ilike(category.strip()))

        if stock_status == StockStatusFilter.LOW_STOCK:
            query = query.where(
                (InventoryLevel.current_stock <= InventoryLevel.reorder_point)
                & (InventoryLevel.current_stock > 0)
            )
        elif stock_status == StockStatusFilter.OUT_OF_STOCK:
            query = query.where(InventoryLevel.current_stock == 0)
        elif stock_status == StockStatusFilter.HEALTHY:
            query = query.where(InventoryLevel.current_stock > InventoryLevel.reorder_point)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        paginated_query = query.order_by(Product.name.asc()).offset(offset).limit(size)
        result = await db.execute(paginated_query)
        rows = result.all()

        inventory_records = []
        for product, inv in rows:
            preferred_sp = next(
                (sp for sp in product.supplier_products if sp.is_preferred),
                product.supplier_products[0] if product.supplier_products else None,
            )

            status_label = "OUT_OF_STOCK" if inv.current_stock == 0 else (
                "LOW_STOCK" if inv.current_stock <= inv.reorder_point else "HEALTHY"
            )

            inventory_records.append({
                "product_id": product.id,
                "sku": product.sku,
                "product_name": product.name,
                "category": product.category,
                "unit": product.unit,
                "unit_price": product.unit_price,
                "current_stock": inv.current_stock,
                "reserved_stock": inv.reserved_stock,
                "available_stock": inv.available_stock,
                "reorder_point": inv.reorder_point,
                "reorder_quantity": inv.reorder_quantity,
                "max_stock": inv.max_stock,
                "warehouse_location": inv.warehouse_location,
                "stock_status": status_label,
                "preferred_supplier_id": preferred_sp.supplier_id if preferred_sp else None,
                "preferred_supplier_name": preferred_sp.supplier.name if preferred_sp else None,
            })

        return inventory_records, total

    @staticmethod
    async def get_low_stock_items(
        db: AsyncSession,
        category: Optional[str] = None,
    ) -> List[LowStockItemResponse]:
        """Detect and return low-stock products with calculated shortages and replenishment estimates."""
        query = (
            select(Product, InventoryLevel)
            .join(InventoryLevel, Product.id == InventoryLevel.product_id)
            .where(InventoryLevel.current_stock <= InventoryLevel.reorder_point)
            .options(
                selectinload(Product.supplier_products).joinedload(SupplierProduct.supplier)
            )
        )

        if category:
            query = query.where(Product.category.ilike(category.strip()))

        query = query.order_by(InventoryLevel.current_stock.asc())
        result = await db.execute(query)
        rows = result.all()

        low_stock_items = []
        for product, inv in rows:
            preferred_sp = next(
                (sp for sp in product.supplier_products if sp.is_preferred),
                product.supplier_products[0] if product.supplier_products else None,
            )

            deficit = max(0, inv.reorder_point - inv.current_stock)
            suggested_qty = max(inv.reorder_quantity, inv.max_stock - inv.current_stock)

            est_unit_cost = preferred_sp.unit_cost if preferred_sp else None
            est_reorder_cost = (
                Decimal(str(suggested_qty)) * est_unit_cost if est_unit_cost is not None else None
            )

            low_stock_items.append(
                LowStockItemResponse(
                    product_id=product.id,
                    sku=product.sku,
                    product_name=product.name,
                    category=product.category,
                    current_stock=inv.current_stock,
                    reserved_stock=inv.reserved_stock,
                    available_stock=inv.available_stock,
                    reorder_point=inv.reorder_point,
                    reorder_quantity=inv.reorder_quantity,
                    deficit=deficit,
                    suggested_order_qty=suggested_qty,
                    preferred_supplier_id=preferred_sp.supplier_id if preferred_sp else None,
                    preferred_supplier_name=preferred_sp.supplier.name if preferred_sp else None,
                    estimated_unit_cost=est_unit_cost,
                    estimated_reorder_cost=est_reorder_cost,
                )
            )

        return low_stock_items

    @staticmethod
    async def calculate_reorder_recommendation(
        db: AsyncSession,
        product_id: int,
        target_stock_level: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> dict:
        """
        Deterministic replenishment calculation:
        1. Validates product and inventory exist.
        2. Determines effective target ceiling (custom target_stock_level or product max_stock).
        3. Computes replenishment deficit: max(0, target - current_stock).
        4. Adjusts suggested quantity to respect supplier Minimum Order Quantity (MOQ) and batch increments.
        5. Computes total estimated cost using verified supplier catalog pricing.
        """
        query = (
            select(Product, InventoryLevel)
            .join(InventoryLevel, Product.id == InventoryLevel.product_id)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.supplier_products).joinedload(SupplierProduct.supplier)
            )
        )
        result = await db.execute(query)
        row = result.first()

        if not row:
            raise NotFoundException("Product", product_id)

        product, inv = row

        if not product.supplier_products:
            raise BadRequestException(f"Product '{product.name}' (SKU: {product.sku}) has no associated suppliers.")

        # Determine supplier
        selected_sp = None
        if supplier_id is not None:
            selected_sp = next(
                (sp for sp in product.supplier_products if sp.supplier_id == supplier_id),
                None,
            )
            if not selected_sp:
                raise BadRequestException(
                    f"Supplier ID {supplier_id} does not supply Product ID {product_id} ('{product.name}')."
                )
        else:
            # Pick preferred supplier or first supplier
            selected_sp = next(
                (sp for sp in product.supplier_products if sp.is_preferred),
                product.supplier_products[0],
            )

        # Target stock calculation
        effective_target = target_stock_level if target_stock_level is not None else inv.max_stock
        if effective_target < inv.reorder_point:
            raise BadRequestException(
                f"Target stock level ({effective_target}) cannot be lower than reorder point ({inv.reorder_point})."
            )

        raw_deficit = max(0, effective_target - inv.current_stock)

        # Baseline suggested order quantity
        suggested_qty = raw_deficit if raw_deficit > 0 else inv.reorder_quantity

        # Enforce supplier Minimum Order Quantity (MOQ)
        moq = selected_sp.min_order_qty
        if suggested_qty < moq:
            suggested_qty = moq

        unit_cost = selected_sp.unit_cost
        estimated_total_cost = Decimal(str(suggested_qty)) * unit_cost

        return {
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "category": product.category,
            "current_stock": inv.current_stock,
            "reorder_point": inv.reorder_point,
            "max_stock": inv.max_stock,
            "target_stock_level": effective_target,
            "is_low_stock": inv.is_low_stock,
            "deficit": raw_deficit,
            "suggested_order_qty": suggested_qty,
            "supplier_id": selected_sp.supplier_id,
            "supplier_name": selected_sp.supplier.name,
            "supplier_code": selected_sp.supplier.code,
            "supplier_moq": moq,
            "lead_time_days": selected_sp.lead_time_days or selected_sp.supplier.lead_time_days,
            "unit_cost": unit_cost,
            "estimated_total_cost": estimated_total_cost,
            "currency": "USD",
        }

    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        product_id: int,
        payload: StockAdjustmentRequest,
        actor_type: ActorType = ActorType.USER,
        actor_id: str = "manual_operator",
    ) -> InventoryLevel:
        """Adjust product stock quantity with audited tracking."""
        query = select(InventoryLevel).where(InventoryLevel.product_id == product_id)
        inv = (await db.execute(query)).scalar_one_or_none()
        if not inv:
            raise NotFoundException("Inventory for Product", product_id)

        old_stock = inv.current_stock
        new_stock = old_stock + payload.quantity_delta
        if new_stock < 0:
            raise BadRequestException(
                f"Cannot reduce stock by {abs(payload.quantity_delta)}. Current stock is {old_stock}."
            )

        inv.current_stock = new_stock
        if payload.location:
            inv.warehouse_location = payload.location
        if payload.quantity_delta > 0:
            inv.last_restocked_at = datetime.now(timezone.utc)

        audit = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action="STOCK_ADJUSTMENT",
            entity_type="InventoryLevel",
            entity_id=str(inv.id),
            payload_before={"current_stock": old_stock},
            payload_after={"current_stock": new_stock, "delta": payload.quantity_delta},
            description=f"Adjusted stock for product {product_id}. Reason: {payload.reason}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(inv)
        return inv
