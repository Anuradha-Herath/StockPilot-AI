from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique supplier code")
    name: str = Field(..., min_length=2, max_length=200)
    contact_person: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    lead_time_days: int = Field(default=3, ge=0)
    rating: Decimal = Field(default=Decimal("4.50"), ge=Decimal("1.00"), le=Decimal("5.00"))
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    lead_time_days: Optional[int] = Field(None, ge=0)
    rating: Optional[Decimal] = Field(None, ge=Decimal("1.00"), le=Decimal("5.00"))
    is_active: Optional[bool] = None


class SupplierProductItem(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    product_category: str
    supplier_sku: Optional[str]
    unit_cost: Decimal
    min_order_qty: int
    lead_time_days: int
    is_preferred: bool

    model_config = ConfigDict(from_attributes=True)


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime
    updated_at: datetime
    total_products_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SupplierDetailResponse(SupplierResponse):
    supplied_products: List[SupplierProductItem] = []

    model_config = ConfigDict(from_attributes=True)
