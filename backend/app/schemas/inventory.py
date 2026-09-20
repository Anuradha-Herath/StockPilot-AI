from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InventoryLevelBase(BaseModel):
    current_stock: int = Field(..., ge=0, description="Current physically available stock")
    reserved_stock: int = Field(default=0, ge=0, description="Reserved stock for open orders")
    reorder_point: int = Field(..., ge=0, description="Stock threshold triggering replenishment")
    reorder_quantity: int = Field(default=50, ge=1, description="Standard batch order quantity")
    max_stock: int = Field(..., ge=1, description="Maximum storage capacity")
    warehouse_location: Optional[str] = Field(None, max_length=100)


class InventoryLevelResponse(InventoryLevelBase):
    id: int
    product_id: int
    available_stock: int
    is_low_stock: bool
    stock_status: str
    last_restocked_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LowStockItemResponse(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category: str
    current_stock: int
    reserved_stock: int
    available_stock: int
    reorder_point: int
    reorder_quantity: int
    deficit: int = Field(..., description="Calculated shortage: max(0, reorder_point - current_stock)")
    suggested_order_qty: int = Field(..., description="Suggested units to replenish up to target or standard batch")
    preferred_supplier_id: Optional[int] = None
    preferred_supplier_name: Optional[str] = None
    estimated_unit_cost: Optional[Decimal] = None
    estimated_reorder_cost: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class StockSummaryResponse(BaseModel):
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_inventory_valuation: Decimal
    healthy_stock_count: int


class StockAdjustmentRequest(BaseModel):
    quantity_delta: int = Field(..., description="Positive for addition, negative for reduction")
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for stock adjustment")
    location: Optional[str] = None
