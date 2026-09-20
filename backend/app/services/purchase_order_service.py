import logging
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import NotFoundException
from app.db.models.product import Product
from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.schemas.purchase_order import PurchaseOrderItemResponse, PurchaseOrderResponse

logger = logging.getLogger("stockpilot.purchase_order")


class PurchaseOrderService:
    @staticmethod
    def _map_to_response(order: PurchaseOrder) -> PurchaseOrderResponse:
        items_resp = [
            PurchaseOrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_sku=item.product.sku if item.product else None,
                product_name=item.product.name if item.product else None,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                line_total=item.line_total,
                received_quantity=item.received_quantity,
            )
            for item in order.items
        ]

        return PurchaseOrderResponse(
            id=order.id,
            order_number=order.order_number,
            supplier_id=order.supplier_id,
            supplier_name=order.supplier.name if order.supplier else None,
            status=order.status,
            total_amount=order.total_amount,
            currency=order.currency,
            created_by_id=order.created_by_id,
            approved_by_id=order.approved_by_id,
            approved_at=order.approved_at,
            expected_delivery_date=order.expected_delivery_date,
            notes=order.notes,
            items=items_resp,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    @classmethod
    async def list_purchase_orders(
        cls,
        db: AsyncSession,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[PurchaseOrderResponse], int]:
        """Lists purchase orders with optional filtering and pagination."""
        query = (
            select(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
            .order_by(PurchaseOrder.created_at.desc())
        )

        count_query = select(func.count(PurchaseOrder.id))

        if status is not None:
            query = query.where(PurchaseOrder.status == status)
            count_query = count_query.where(PurchaseOrder.status == status)

        if supplier_id is not None:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)
            count_query = count_query.where(PurchaseOrder.supplier_id == supplier_id)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        orders = result.scalars().all()

        return [cls._map_to_response(o) for o in orders], total

    @classmethod
    async def get_order_by_id(cls, db: AsyncSession, order_id: int) -> PurchaseOrderResponse:
        """Retrieves a single purchase order by primary key ID."""
        query = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == order_id)
            .options(
                joinedload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise NotFoundException("PurchaseOrder", order_id)

        return cls._map_to_response(order)

    @classmethod
    async def get_order_by_number(cls, db: AsyncSession, order_number: str) -> PurchaseOrderResponse:
        """Retrieves a single purchase order by order number."""
        query = (
            select(PurchaseOrder)
            .where(PurchaseOrder.order_number == order_number)
            .options(
                joinedload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise NotFoundException("PurchaseOrder", order_number)

        return cls._map_to_response(order)
