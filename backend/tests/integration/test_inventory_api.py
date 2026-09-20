from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_inventory_summary_and_low_stock(client: AsyncClient, seeded_db_session: AsyncSession):
    # Test inventory summary
    summary_resp = await client.get("/api/v1/inventory/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_products"] == 2
    assert summary["low_stock_count"] == 1  # Whole milk (5 <= 20)
    assert summary["healthy_stock_count"] == 1  # Bread (40 > 15)

    # Test low stock items endpoint
    low_stock_resp = await client.get("/api/v1/inventory/low-stock")
    assert low_stock_resp.status_code == 200
    items = low_stock_resp.json()
    assert len(items) == 1
    low_item = items[0]
    assert low_item["sku"] == "TEST-SKU-MILK"
    assert low_item["current_stock"] == 5
    assert low_item["reorder_point"] == 20
    assert low_item["deficit"] == 15  # 20 - 5
    assert low_item["preferred_supplier_name"] == "Test Dairy Co."


@pytest.mark.asyncio
async def test_stock_adjustment_flow(client: AsyncClient, seeded_db_session: AsyncSession):
    # Adjust stock for product 1 (Whole milk)
    # Increase stock by 20 units
    adjust_payload = {
        "quantity_delta": 20,
        "reason": "Shipment received from supplier",
        "location": "AISLE-01-EXPANDED",
    }
    adjust_resp = await client.post("/api/v1/inventory/1/adjust", json=adjust_payload)
    assert adjust_resp.status_code == 200
    updated_inv = adjust_resp.json()
    assert updated_inv["current_stock"] == 25  # 5 + 20
    assert updated_inv["warehouse_location"] == "AISLE-01-EXPANDED"

    # Now verify it's no longer low stock
    low_stock_resp = await client.get("/api/v1/inventory/low-stock")
    items = low_stock_resp.json()
    assert len(items) == 0


@pytest.mark.asyncio
async def test_stock_adjustment_cannot_go_negative(client: AsyncClient, seeded_db_session: AsyncSession):
    # Product 1 has 5 stock. Attempt to reduce by 10.
    adjust_payload = {
        "quantity_delta": -10,
        "reason": "Damage writeoff",
    }
    adjust_resp = await client.post("/api/v1/inventory/1/adjust", json=adjust_payload)
    assert adjust_resp.status_code == 400 or adjust_resp.status_code == 500
