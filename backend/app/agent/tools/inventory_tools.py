from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import ToolResult, safe_tool_executor
from app.agent.tools.schemas import (
    CalculateReorderRecommendationInput,
    CalculateReorderRecommendationOutput,
    FindLowStockProductsInput,
    FindLowStockProductsOutput,
    GetInventoryInput,
    GetInventoryOutput,
    GetSupplierOptionsInput,
    GetSupplierOptionsOutput,
    InventoryRecordItem,
    LowStockAlertItem,
    ProductSummaryItem,
    SearchProductsInput,
    SearchProductsOutput,
    SupplierOptionItem,
)
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService


@safe_tool_executor("search_products", max_retries=2, timeout_seconds=8.0)
async def search_products(
    db: AsyncSession,
    args: SearchProductsInput,
) -> ToolResult[SearchProductsOutput]:
    """
    Searches the supermarket product catalog by SKU, name, or category.
    Returns product details, prices, and stock status indicators.
    """
    products, total = await ProductService.get_products(
        db=db,
        search=args.query,
        category=args.category,
        page=1,
        size=args.limit,
    )

    items = [
        ProductSummaryItem(
            product_id=p.id,
            sku=p.sku,
            name=p.name,
            category=p.category,
            unit=p.unit,
            unit_price=p.unit_price,
            current_stock=p.inventory.current_stock if p.inventory else 0,
            reorder_point=p.inventory.reorder_point if p.inventory else 0,
            is_low_stock=p.inventory.is_low_stock if p.inventory else False,
        )
        for p in products
    ]

    return ToolResult.ok(
        SearchProductsOutput(
            total_found=total,
            products=items,
        )
    )


@safe_tool_executor("get_inventory", max_retries=2, timeout_seconds=8.0)
async def get_inventory(
    db: AsyncSession,
    args: GetInventoryInput,
) -> ToolResult[GetInventoryOutput]:
    """
    Retrieves inventory levels and storage coordinates across products.
    Supports filtering by stock health status (ALL, HEALTHY, LOW_STOCK, OUT_OF_STOCK).
    """
    records, total = await InventoryService.lookup_inventory(
        db=db,
        product_id=args.product_id,
        sku=args.sku,
        search=args.search,
        category=args.category,
        stock_status=args.stock_status,
        page=args.page,
        size=args.size,
    )

    items = [
        InventoryRecordItem(
            product_id=r["product_id"],
            sku=r["sku"],
            product_name=r["product_name"],
            category=r["category"],
            unit=r["unit"],
            unit_price=r["unit_price"],
            current_stock=r["current_stock"],
            reserved_stock=r["reserved_stock"],
            available_stock=r["available_stock"],
            reorder_point=r["reorder_point"],
            reorder_quantity=r["reorder_quantity"],
            max_stock=r["max_stock"],
            warehouse_location=r["warehouse_location"],
            stock_status=r["stock_status"],
            preferred_supplier_id=r["preferred_supplier_id"],
            preferred_supplier_name=r["preferred_supplier_name"],
        )
        for r in records
    ]

    return ToolResult.ok(
        GetInventoryOutput(
            total_count=total,
            page=args.page,
            items=items,
        )
    )


@safe_tool_executor("find_low_stock_products", max_retries=2, timeout_seconds=8.0)
async def find_low_stock_products(
    db: AsyncSession,
    args: FindLowStockProductsInput,
) -> ToolResult[FindLowStockProductsOutput]:
    """
    Identifies all products currently at or below their reorder threshold.
    Includes calculated stock deficits and replenishment cost estimates.
    """
    low_items = await InventoryService.get_low_stock_items(
        db=db,
        category=args.category,
    )

    items = [
        LowStockAlertItem(
            product_id=item.product_id,
            sku=item.sku,
            product_name=item.product_name,
            category=item.category,
            current_stock=item.current_stock,
            reorder_point=item.reorder_point,
            deficit=item.deficit,
            suggested_order_qty=item.suggested_order_qty,
            preferred_supplier_id=item.preferred_supplier_id,
            preferred_supplier_name=item.preferred_supplier_name,
            estimated_unit_cost=item.estimated_unit_cost,
            estimated_reorder_cost=item.estimated_reorder_cost,
        )
        for item in low_items
    ]

    return ToolResult.ok(
        FindLowStockProductsOutput(
            low_stock_count=len(items),
            items=items,
        )
    )


@safe_tool_executor("get_supplier_options", max_retries=2, timeout_seconds=8.0)
async def get_supplier_options(
    db: AsyncSession,
    args: GetSupplierOptionsInput,
) -> ToolResult[GetSupplierOptionsOutput]:
    """
    Retrieves all registered suppliers that provide a specific product.
    Returns wholesale unit costs, lead times, MOQ, and supplier reliability ratings.
    """
    product = await ProductService.get_product_by_id(db=db, product_id=args.product_id)

    supplier_options = [
        SupplierOptionItem(
            supplier_id=sup.supplier_id,
            supplier_name=sup.supplier_name,
            supplier_code=sup.supplier_code,
            supplier_sku=sup.supplier_sku,
            unit_cost=sup.unit_cost,
            min_order_qty=sup.min_order_qty,
            lead_time_days=sup.lead_time_days,
            rating=Decimal("4.50"),  # Standard default rating
            is_preferred=sup.is_preferred,
        )
        for sup in product.suppliers
    ]

    return ToolResult.ok(
        GetSupplierOptionsOutput(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            available_suppliers=supplier_options,
        )
    )


@safe_tool_executor("calculate_reorder_recommendation", max_retries=1, timeout_seconds=8.0)
async def calculate_reorder_recommendation(
    db: AsyncSession,
    args: CalculateReorderRecommendationInput,
) -> ToolResult[CalculateReorderRecommendationOutput]:
    """
    Calculates the exact replenishment quantity and estimated purchase order cost.
    Considers current stock, target ceilings, supplier MOQ constraints, and wholesale pricing.
    """
    recommendation = await InventoryService.calculate_reorder_recommendation(
        db=db,
        product_id=args.product_id,
        target_stock_level=args.target_stock_level,
        supplier_id=args.supplier_id,
    )

    return ToolResult.ok(
        CalculateReorderRecommendationOutput(
            product_id=recommendation["product_id"],
            sku=recommendation["sku"],
            product_name=recommendation["product_name"],
            category=recommendation["category"],
            current_stock=recommendation["current_stock"],
            reorder_point=recommendation["reorder_point"],
            max_stock=recommendation["max_stock"],
            target_stock_level=recommendation["target_stock_level"],
            is_low_stock=recommendation["is_low_stock"],
            deficit=recommendation["deficit"],
            suggested_order_qty=recommendation["suggested_order_qty"],
            supplier_id=recommendation["supplier_id"],
            supplier_name=recommendation["supplier_name"],
            supplier_code=recommendation["supplier_code"],
            supplier_moq=recommendation["supplier_moq"],
            lead_time_days=recommendation["lead_time_days"],
            unit_cost=recommendation["unit_cost"],
            estimated_total_cost=recommendation["estimated_total_cost"],
            currency=recommendation["currency"],
        )
    )
