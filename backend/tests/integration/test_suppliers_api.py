import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_supplier(client: AsyncClient):
    payload = {
        "code": "SUP-TEST-NEW",
        "name": "Acme Farm Supplies",
        "contact_person": "John Doe",
        "email": "orders@acmefarms.com",
        "phone": "+1-555-1234",
        "lead_time_days": 4,
        "rating": "4.75",
    }
    create_resp = await client.post("/api/v1/suppliers", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["code"] == "SUP-TEST-NEW"
    sup_id = created_data["id"]

    # Retrieve supplier
    get_resp = await client.get(f"/api/v1/suppliers/{sup_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == sup_id
    assert detail["name"] == "Acme Farm Supplies"


@pytest.mark.asyncio
async def test_get_nonexistent_supplier_404(client: AsyncClient):
    response = await client.get("/api/v1/suppliers/99999")
    assert response.status_code == 404
    error = response.json()
    assert error["success"] is False


@pytest.mark.asyncio
async def test_invalid_supplier_email_422(client: AsyncClient):
    payload = {
        "code": "SUP-INVALID",
        "name": "Invalid Supplier",
        "email": "not-a-valid-email-address",
    }
    response = await client.post("/api/v1/suppliers", json=payload)
    assert response.status_code == 422
