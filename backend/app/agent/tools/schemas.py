from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.models.purchase_request import PriorityLevel, PurchaseRequestStatus
from app.services.inventory_service import StockStatusFilter


# ==========================================
# Tool 1: search_products
# ==========================================
class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(None, description="Keywords to match SKU, name or category")
    category: Optional[str] = Field(None, description="Exact category name (e.g. 'Dairy', 'Produce', 'Beverages')")
    limit: int = Field(10, ge=1, le=50, description="Max number of items to return")


class ProductSummaryItem(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    unit: str
    unit_price: Decimal
    current_stock: int
    reorder_point: int
    is_low_stock: bool


class SearchProductsOutput(BaseModel):
    total_found: int
    products: List[ProductSummaryItem]


# ==========================================
# Tool 2: get_inventory
# ==========================================
class GetInventoryInput(BaseModel):
    product_id: Optional[int] = Field(None, description="Query by specific Product ID")
    sku: Optional[str] = Field(None, description="Query by specific SKU code")
    search: Optional[str] = Field(None, description="Search term for name/SKU/category")
    category: Optional[str] = Field(None, description="Category filter")
    stock_status: StockStatusFilter = Field(
        StockStatusFilter.ALL,
        description="Filter by stock health: ALL, HEALTHY, LOW_STOCK, OUT_OF_STOCK",
    )
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=50, description="Items per page")


class InventoryRecordItem(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category: str
    unit: str
    unit_price: Decimal
    current_stock: int
    reserved_stock: int
    available_stock: int
    reorder_point: int
    reorder_quantity: int
    max_stock: int
    warehouse_location: Optional[str] = None
    stock_status: str
    preferred_supplier_id: Optional[int] = None
    preferred_supplier_name: Optional[str] = None


class GetInventoryOutput(BaseModel):
    total_count: int
    page: int
    items: List[InventoryRecordItem]


# ==========================================
# Tool 3: find_low_stock_products
# ==========================================
class FindLowStockProductsInput(BaseModel):
    category: Optional[str] = Field(None, description="Filter low stock items by category")


class LowStockAlertItem(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category: str
    current_stock: int
    reorder_point: int
    deficit: int
    suggested_order_qty: int
    preferred_supplier_id: Optional[int] = None
    preferred_supplier_name: Optional[str] = None
    estimated_unit_cost: Optional[Decimal] = None
    estimated_reorder_cost: Optional[Decimal] = None


class FindLowStockProductsOutput(BaseModel):
    low_stock_count: int
    items: List[LowStockAlertItem]


# ==========================================
# Tool 4: get_supplier_options
# ==========================================
class GetSupplierOptionsInput(BaseModel):
    product_id: int = Field(..., ge=1, description="Product ID to find available suppliers for")


class SupplierOptionItem(BaseModel):
    supplier_id: int
    supplier_name: str
    supplier_code: str
    supplier_sku: Optional[str]
    unit_cost: Decimal
    min_order_qty: int
    lead_time_days: int
    rating: Decimal
    is_preferred: bool


class GetSupplierOptionsOutput(BaseModel):
    product_id: int
    product_name: str
    sku: str
    available_suppliers: List[SupplierOptionItem]


# ==========================================
# Tool 5: calculate_reorder_recommendation
# ==========================================
class CalculateReorderRecommendationInput(BaseModel):
    product_id: int = Field(..., ge=1, description="Product ID to compute replenishment for")
    target_stock_level: Optional[int] = Field(
        None, ge=1, description="Optional custom target stock ceiling (defaults to product max_stock)"
    )
    supplier_id: Optional[int] = Field(
        None, ge=1, description="Specific supplier ID to evaluate (defaults to preferred supplier)"
    )


class CalculateReorderRecommendationOutput(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category: str
    current_stock: int
    reorder_point: int
    max_stock: int
    target_stock_level: int
    is_low_stock: bool
    deficit: int
    suggested_order_qty: int
    supplier_id: int
    supplier_name: str
    supplier_code: str
    supplier_moq: int
    lead_time_days: int
    unit_cost: Decimal
    estimated_total_cost: Decimal
    currency: str = "USD"


# ==========================================
# Tool 6: create_draft_purchase_request
# ==========================================
class PurchaseRequestItemInput(BaseModel):
    product_id: int = Field(..., ge=1, description="Valid Product ID to purchase")
    quantity: int = Field(..., ge=1, description="Number of units to request (must be >= 1)")


class CreateDraftPurchaseRequestInput(BaseModel):
    supplier_id: int = Field(..., ge=1, description="Supplier ID from whom to order")
    items: List[PurchaseRequestItemInput] = Field(
        ..., min_length=1, description="List of unique product IDs and requested quantities"
    )
    priority: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Priority: LOW, MEDIUM, HIGH, CRITICAL")
    reason: Optional[str] = Field(
        None, description="Business justification (e.g. 'Low stock replenishment for dairy aisle')"
    )


class PurchaseRequestLineItemSummary(BaseModel):
    id: int
    product_id: int
    product_sku: Optional[str]
    product_name: Optional[str]
    quantity: int
    estimated_unit_cost: Decimal
    total_cost: Decimal


class CreateDraftPurchaseRequestOutput(BaseModel):
    id: int
    request_number: str
    supplier_id: int
    supplier_name: str
    status: PurchaseRequestStatus
    priority: PriorityLevel
    reason: Optional[str]
    total_estimated_cost: Decimal
    items: List[PurchaseRequestLineItemSummary]
    created_at: str
    proposal_version_hash: Optional[str] = None
    next_step: str = "Proposal registered in PENDING_APPROVAL state. Awaiting manager approval before PO issuance."


# ==========================================
# Tool 7: get_purchase_request_status
# ==========================================
class GetPurchaseRequestStatusInput(BaseModel):
    request_number: Optional[str] = Field(None, description="Purchase Request Number e.g. 'PR-20260919-AB12'")
    request_id: Optional[int] = Field(None, ge=1, description="Purchase Request ID")


class GetPurchaseRequestStatusOutput(BaseModel):
    id: int
    request_number: str
    supplier_id: int
    supplier_name: str
    status: PurchaseRequestStatus
    priority: PriorityLevel
    total_estimated_cost: Decimal
    item_count: int
    items: List[PurchaseRequestLineItemSummary]
    created_at: str
