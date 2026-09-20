import math
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import DBSessionDep, PaginationDep
from app.db.models.purchase_order import PurchaseOrderStatus
from app.schemas.common import PaginatedResponse
from app.schemas.purchase_order import PurchaseOrderResponse
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


@router.get("", response_model=PaginatedResponse[PurchaseOrderResponse])
async def list_purchase_orders(
    db: DBSessionDep,
    pagination: PaginationDep,
    status_filter: Optional[PurchaseOrderStatus] = Query(None, alias="status"),
    supplier_id: Optional[int] = Query(None),
):
    """List purchase orders with optional status and supplier filters."""
    orders, total = await PurchaseOrderService.list_purchase_orders(
        db=db,
        status=status_filter,
        supplier_id=supplier_id,
        page=pagination.page,
        size=pagination.size,
    )
    pages = math.ceil(total / pagination.size) if total > 0 else 1

    return PaginatedResponse[PurchaseOrderResponse](
        items=orders,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(order_id: int, db: DBSessionDep):
    """Retrieve purchase order details by ID."""
    return await PurchaseOrderService.get_order_by_id(db=db, order_id=order_id)
