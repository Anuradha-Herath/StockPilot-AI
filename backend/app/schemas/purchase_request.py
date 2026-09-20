from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.purchase_request import PriorityLevel, PurchaseRequestStatus


class PurchaseRequestItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    estimated_unit_cost: Decimal = Field(..., ge=Decimal("0.00"))


class PurchaseRequestItemResponse(PurchaseRequestItemBase):
    id: int
    total_cost: Decimal
    product_sku: Optional[str] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequestCreate(BaseModel):
    supplier_id: int
    priority: PriorityLevel = PriorityLevel.MEDIUM
    reason: Optional[str] = None
    items: List[PurchaseRequestItemBase] = Field(..., min_length=1)


class PurchaseRequestResponse(BaseModel):
    id: int
    request_number: str
    requester_id: Optional[int]
    supplier_id: int
    supplier_name: Optional[str] = None
    status: PurchaseRequestStatus
    priority: PriorityLevel
    reason: Optional[str]
    total_estimated_cost: Decimal
    items: List[PurchaseRequestItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
