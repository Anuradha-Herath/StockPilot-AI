from decimal import Decimal
import pytest
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
    CreateDraftPurchaseRequestInput,
    FindLowStockProductsInput,
    GetInventoryInput,
    GetPurchaseRequestStatusInput,
    GetSupplierOptionsInput,
    PurchaseRequestItemInput,
    SearchProductsInput,
)
from app.db.models.purchase_request import PriorityLevel, PurchaseRequestStatus
from app.services.inventory_service import StockStatusFilter


@pytest.mark.asyncio
async def test_tool_search_products(seeded_db_session):
    args = SearchProductsInput(query="Milk", limit=5)
    res = await search_products(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data is not None
    assert res.data.total_found >= 1
    assert res.data.products[0].sku == "TEST-SKU-MILK"


@pytest.mark.asyncio
async def test_tool_get_inventory_low_stock_filter(seeded_db_session):
    args = GetInventoryInput(stock_status=StockStatusFilter.LOW_STOCK)
    res = await get_inventory(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data.total_count == 1
    assert res.data.items[0].sku == "TEST-SKU-MILK"
    assert res.data.items[0].stock_status == "LOW_STOCK"


@pytest.mark.asyncio
async def test_tool_find_low_stock_products(seeded_db_session):
    args = FindLowStockProductsInput()
    res = await find_low_stock_products(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data.low_stock_count == 1
    assert res.data.items[0].sku == "TEST-SKU-MILK"
    assert res.data.items[0].suggested_order_qty == 95


@pytest.mark.asyncio
async def test_tool_get_supplier_options(seeded_db_session):
    args = GetSupplierOptionsInput(product_id=1)
    res = await get_supplier_options(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data.product_id == 1
    assert len(res.data.available_suppliers) == 1
    sup = res.data.available_suppliers[0]
    assert sup.supplier_code == "TEST-SUP-01"
    assert sup.unit_cost == Decimal("3.00")


@pytest.mark.asyncio
async def test_tool_calculate_reorder_recommendation(seeded_db_session):
    args = CalculateReorderRecommendationInput(product_id=1, target_stock_level=80)
    res = await calculate_reorder_recommendation(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data.product_id == 1
    assert res.data.target_stock_level == 80
    assert res.data.suggested_order_qty == 75  # 80 - 5
    assert res.data.estimated_total_cost == Decimal("225.00")  # 75 * 3.00


@pytest.mark.asyncio
async def test_tool_create_draft_purchase_request(seeded_db_session):
    args = CreateDraftPurchaseRequestInput(
        supplier_id=1,
        items=[PurchaseRequestItemInput(product_id=1, quantity=30)],
        priority=PriorityLevel.MEDIUM,
        reason="Stock replenishment via tool",
    )
    res = await create_draft_purchase_request(db=seeded_db_session, args=args)

    assert res.success is True
    assert res.data.status == PurchaseRequestStatus.PENDING_APPROVAL
    assert res.data.total_estimated_cost == Decimal("90.00")  # 30 * 3.00
    assert "manager approval" in res.data.next_step.lower()

    # Test status lookup tool
    status_args = GetPurchaseRequestStatusInput(request_number=res.data.request_number)
    status_res = await get_purchase_request_status(db=seeded_db_session, args=status_args)

    assert status_res.success is True
    assert status_res.data.request_number == res.data.request_number
    assert status_res.data.status == PurchaseRequestStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_tool_safe_exception_trapping_on_invalid_input(seeded_db_session):
    # Attempt to request an invalid/unsupplied product ID
    args = CreateDraftPurchaseRequestInput(
        supplier_id=1,
        items=[PurchaseRequestItemInput(product_id=99999, quantity=10)],
    )
    res = await create_draft_purchase_request(db=seeded_db_session, args=args)

    # Must return ToolResult.fail and not crash the process
    assert res.success is False
    assert res.error is not None
    assert "BadRequestException" in res.error.code
    assert "does not exist in catalog" in res.error.message
