from typing import Any, Callable, Dict
from pydantic import BaseModel

from app.agent.tools.inventory_tools import (
    calculate_reorder_recommendation,
    find_low_stock_products,
    get_inventory,
    get_supplier_options,
    search_products,
)
from app.agent.tools.procurement_tools import (
    create_draft_purchase_request,
    get_purchase_request_status,
)
from app.agent.tools.schemas import (
    CalculateReorderRecommendationInput,
    CalculateReorderRecommendationOutput,
    CreateDraftPurchaseRequestInput,
    CreateDraftPurchaseRequestOutput,
    FindLowStockProductsInput,
    FindLowStockProductsOutput,
    GetInventoryInput,
    GetInventoryOutput,
    GetPurchaseRequestStatusInput,
    GetPurchaseRequestStatusOutput,
    GetSupplierOptionsInput,
    GetSupplierOptionsOutput,
    SearchProductsInput,
    SearchProductsOutput,
)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    is_mutation: bool = False  # If true, modifies draft state; if false, read-only


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "search_products": {
        "function": search_products,
        "description": "Searches product catalog by SKU, name, or category with price and stock summary.",
        "input_schema": SearchProductsInput,
        "output_schema": SearchProductsOutput,
        "is_mutation": False,
    },
    "get_inventory": {
        "function": get_inventory,
        "description": "Retrieves detailed inventory levels, warehouse locations, and stock health status.",
        "input_schema": GetInventoryInput,
        "output_schema": GetInventoryOutput,
        "is_mutation": False,
    },
    "find_low_stock_products": {
        "function": find_low_stock_products,
        "description": "Identifies products currently at or below their reorder threshold with deficits.",
        "input_schema": FindLowStockProductsInput,
        "output_schema": FindLowStockProductsOutput,
        "is_mutation": False,
    },
    "get_supplier_options": {
        "function": get_supplier_options,
        "description": "Lists available suppliers for a product with unit costs, lead times, ratings, and MOQs.",
        "input_schema": GetSupplierOptionsInput,
        "output_schema": GetSupplierOptionsOutput,
        "is_mutation": False,
    },
    "calculate_reorder_recommendation": {
        "function": calculate_reorder_recommendation,
        "description": "Computes suggested replenishment batch size, target stock deficit, and estimated cost.",
        "input_schema": CalculateReorderRecommendationInput,
        "output_schema": CalculateReorderRecommendationOutput,
        "is_mutation": False,
    },
    "create_draft_purchase_request": {
        "function": create_draft_purchase_request,
        "description": "Creates a draft purchase request for manager review. Does NOT place financial orders.",
        "input_schema": CreateDraftPurchaseRequestInput,
        "output_schema": CreateDraftPurchaseRequestOutput,
        "is_mutation": True,  # Creates draft record
    },
    "get_purchase_request_status": {
        "function": get_purchase_request_status,
        "description": "Checks the status, approval progress, and item breakdown of a purchase request.",
        "input_schema": GetPurchaseRequestStatusInput,
        "output_schema": GetPurchaseRequestStatusOutput,
        "is_mutation": False,
    },
}
