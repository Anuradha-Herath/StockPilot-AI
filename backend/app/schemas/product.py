from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.inventory import InventoryLevelResponse


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=50, description="Stock Keeping Unit (Unique)")
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=2, max_length=100)
    unit: str = Field(default="unit", max_length=20)
    unit_price: Decimal = Field(..., ge=Decimal("0.00"), description="Retail selling price per unit")
    is_active: bool = True


class ProductCreate(ProductBase):
    initial_stock: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, ge=1)
    max_stock: int = Field(default=100, ge=1)
    warehouse_location: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    unit_price: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    is_active: Optional[bool] = None


class ProductSupplierInfo(BaseModel):
    supplier_id: int
    supplier_name: str
    supplier_code: str
    supplier_sku: Optional[str]
    unit_cost: Decimal
    min_order_qty: int
    lead_time_days: int
    is_preferred: bool

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    inventory: Optional[InventoryLevelResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(ProductResponse):
    suppliers: List[ProductSupplierInfo] = []

    model_config = ConfigDict(from_attributes=True)
