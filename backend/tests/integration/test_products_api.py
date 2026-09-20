from decimal import Decimal
import pytest
from httpx import AsyncClient
from app.db.models import Product, InventoryLevel


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient):
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_and_get_product(client: AsyncClient):
    payload = {
        "sku": "SKU-CREATETEST-01",
        "name": "Organic Almond Milk",
        "description": "Plant based milk",
        "category": "Beverages",
        "unit": "carton",
        "unit_price": "4.25",
        "is_active": True,
        "initial_stock": 15,
        "reorder_point": 10,
        "reorder_quantity": 30,
        "max_stock": 60,
        "warehouse_location": "AISLE-03",
    }
    create_resp = await client.post("/api/v1/products", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["sku"] == "SKU-CREATETEST-01"
    assert created_data["name"] == "Organic Almond Milk"
    prod_id = created_data["id"]

    # Get product detail
    get_resp = await client.get(f"/api/v1/products/{prod_id}")
    assert get_resp.status_code == 200
    detail_data = get_resp.json()
    assert detail_data["id"] == prod_id
    assert detail_data["inventory"]["current_stock"] == 15
    assert detail_data["inventory"]["reorder_point"] == 10


@pytest.mark.asyncio
async def test_get_nonexistent_product_404(client: AsyncClient):
    response = await client.get("/api/v1/products/99999")
    assert response.status_code == 404
    error = response.json()
    assert error["success"] is False
    assert "not found" in error["error"]["message"].lower()


@pytest.mark.asyncio
async def test_create_duplicate_sku_409(client: AsyncClient):
    payload = {
        "sku": "SKU-DUPTEST-01",
        "name": "Duplicate SKU Item",
        "category": "Pantry",
        "unit_price": "2.99",
    }
    first_resp = await client.post("/api/v1/products", json=payload)
    assert first_resp.status_code == 201

    # Attempt to create duplicate
    dup_resp = await client.post("/api/v1/products", json=payload)
    assert dup_resp.status_code == 409
    error = dup_resp.json()
    assert error["success"] is False
    assert "already exists" in error["error"]["message"]


@pytest.mark.asyncio
async def test_invalid_product_validation_422(client: AsyncClient):
    payload = {
        "sku": "X",  # Too short (min_length=2)
        "name": "",
        "category": "",
        "unit_price": "-5.00",  # Negative price
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "ValidationError" in data["error"]["code"]
