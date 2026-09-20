from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product, Supplier, User, UserRole
from app.schemas.purchase_request import PurchaseRequestItemBase
from app.services.approval_service import ApprovalService
from app.services.purchase_request_service import PurchaseRequestService


@pytest.mark.asyncio
async def test_api_submit_approval_endpoint(seeded_client: AsyncClient, seeded_db_session: AsyncSession):
    """Test POST /api/v1/approvals/requests/{id}/submit."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )

    response = await seeded_client.post(
        f"/api/v1/approvals/requests/{req.id}/submit",
        headers={"X-User-Id": str(operator.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_api_get_pending_approvals_endpoint(seeded_client: AsyncClient, seeded_db_session: AsyncSession):
    """Test GET /api/v1/approvals/pending with manager authorization."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=15, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    # 1. Manager access -> 200 OK
    res_mgr = await seeded_client.get("/api/v1/approvals/pending", headers={"X-User-Id": str(manager.id)})
    assert res_mgr.status_code == 200
    pending_items = res_mgr.json()
    assert len(pending_items) >= 1
    assert any(p["request_id"] == req.id for p in pending_items)

    # 2. Operator access -> 403 Forbidden
    res_op = await seeded_client.get("/api/v1/approvals/pending", headers={"X-User-Id": str(operator.id)})
    assert res_op.status_code == 403


@pytest.mark.asyncio
async def test_api_approve_and_order_endpoints(seeded_client: AsyncClient, seeded_db_session: AsyncSession):
    """Full integration test for approving proposal and retrieving issued PO."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=20, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    # Fetch pending to get hash
    pending_res = await seeded_client.get("/api/v1/approvals/pending", headers={"X-User-Id": str(manager.id)})
    pending_item = next(p for p in pending_res.json() if p["request_id"] == req.id)
    proposal_hash = pending_item["proposal_version_hash"]

    # Manager approves via API
    approve_res = await seeded_client.post(
        f"/api/v1/approvals/requests/{req.id}/approve",
        headers={"X-User-Id": str(manager.id)},
        json={
            "proposal_version_hash": proposal_hash,
            "comments": "Approved via manager integration test.",
            "idempotency_key": "idemp-api-test-1",
        },
    )
    assert approve_res.status_code == 200
    exec_data = approve_res.json()
    assert exec_data["purchase_order_id"] is not None
    assert exec_data["status"] == "ISSUED"

    # Query purchase orders endpoint
    po_res = await seeded_client.get(f"/api/v1/purchase-orders/{exec_data['purchase_order_id']}")
    assert po_res.status_code == 200
    po_data = po_res.json()
    assert po_data["order_number"] == exec_data["order_number"]
    assert po_data["status"] == "ISSUED"
    assert po_data["approved_by_id"] == manager.id
    assert len(po_data["items"]) == 1


@pytest.mark.asyncio
async def test_api_reject_endpoint(seeded_client: AsyncClient, seeded_db_session: AsyncSession):
    """Test POST /api/v1/approvals/requests/{id}/reject."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    reject_res = await seeded_client.post(
        f"/api/v1/approvals/requests/{req.id}/reject",
        headers={"X-User-Id": str(manager.id)},
        json={"comments": "Item discontinued by upstream vendor."},
    )
    assert reject_res.status_code == 200
    data = reject_res.json()
    assert data["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_api_expire_stale_endpoint(seeded_client: AsyncClient, seeded_db_session: AsyncSession):
    """Test POST /api/v1/approvals/expire-stale."""
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()

    expire_res = await seeded_client.post(
        "/api/v1/approvals/expire-stale?max_age_hours=48",
        headers={"X-User-Id": str(manager.id)},
    )
    assert expire_res.status_code == 200
    assert "expired_count" in expire_res.json()
