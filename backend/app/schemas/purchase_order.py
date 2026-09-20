from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.purchase_order import PurchaseOrderStatus


class PurchaseOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int
    unit_cost: Decimal
    line_total: Decimal
    received_quantity: int

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    id: int
    order_number: str
    supplier_id: int
    supplier_name: Optional[str] = None
    status: PurchaseOrderStatus
    total_amount: Decimal
    currency: str
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[PurchaseOrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
