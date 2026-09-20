import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_purchase_requests_api_crud(client: AsyncClient, seeded_db_session: AsyncSession):
    # 1. Create a draft purchase request via REST API
    payload = {
        "supplier_id": 1,
        "priority": "HIGH",
        "reason": "Replenishment for dairy section",
        "items": [
            {"product_id": 1, "quantity": 20, "estimated_unit_cost": "0.00"}
        ],
    }
    create_resp = await client.post("/api/v1/purchase-requests", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["status"] == "DRAFT"
    assert created_data["priority"] == "HIGH"
    assert created_data["total_estimated_cost"] == "60.00"
    pr_id = created_data["id"]

    # 2. Get purchase request by ID
    get_resp = await client.get(f"/api/v1/purchase-requests/{pr_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == pr_id
    assert len(detail["items"]) == 1

    # 3. List purchase requests
    list_resp = await client.get("/api/v1/purchase-requests")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1


@pytest.mark.asyncio
async def test_purchase_requests_api_rejects_duplicate_items(
    client: AsyncClient, seeded_db_session: AsyncSession
):
    payload = {
        "supplier_id": 1,
        "items": [
            {"product_id": 1, "quantity": 10, "estimated_unit_cost": "0.00"},
            {"product_id": 1, "quantity": 15, "estimated_unit_cost": "0.00"},
        ],
    }
    resp = await client.post("/api/v1/purchase-requests", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert "Duplicate products" in data["error"]["message"]
