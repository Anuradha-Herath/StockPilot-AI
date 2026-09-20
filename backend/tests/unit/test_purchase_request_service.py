from decimal import Decimal
import pytest
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.models.purchase_request import PriorityLevel, PurchaseRequestStatus
from app.schemas.purchase_request import PurchaseRequestItemBase
from app.services.purchase_request_service import PurchaseRequestService


@pytest.mark.asyncio
async def test_create_draft_purchase_request_success(seeded_db_session):
    items = [
        PurchaseRequestItemBase(product_id=1, quantity=25, estimated_unit_cost=0)
    ]
    pr = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=1,
        items=items,
        priority=PriorityLevel.HIGH,
        reason="Stock deficit replenishment",
    )

    assert pr.id is not None
    assert pr.request_number.startswith("PR-")
    assert pr.status == PurchaseRequestStatus.DRAFT
    assert pr.priority == PriorityLevel.HIGH
    assert pr.total_estimated_cost == Decimal("75.00")  # 25 * 3.00
    assert len(pr.items) == 1
    assert pr.items[0].product_sku == "TEST-SKU-MILK"
    assert pr.items[0].total_cost == Decimal("75.00")


@pytest.mark.asyncio
async def test_create_draft_purchase_request_empty_items(seeded_db_session):
    with pytest.raises(BadRequestException):
        await PurchaseRequestService.create_draft_request(
            db=seeded_db_session,
            supplier_id=1,
            items=[],
        )


@pytest.mark.asyncio
async def test_create_draft_purchase_request_duplicate_products(seeded_db_session):
    items = [
        PurchaseRequestItemBase(product_id=1, quantity=10, estimated_unit_cost=0),
        PurchaseRequestItemBase(product_id=1, quantity=15, estimated_unit_cost=0),
    ]
    with pytest.raises(BadRequestException) as exc_info:
        await PurchaseRequestService.create_draft_request(
            db=seeded_db_session,
            supplier_id=1,
            items=items,
        )
    assert "Duplicate products" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_create_draft_purchase_request_unsupplied_product(seeded_db_session):
    # Supplier 1 only supplies Product 1. Attempting to order Product 2 from Supplier 1.
    items = [
        PurchaseRequestItemBase(product_id=2, quantity=20, estimated_unit_cost=0)
    ]
    with pytest.raises(BadRequestException) as exc_info:
        await PurchaseRequestService.create_draft_request(
            db=seeded_db_session,
            supplier_id=1,
            items=items,
        )
    assert "not supplied by" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_create_draft_purchase_request_nonexistent_supplier(seeded_db_session):
    items = [
        PurchaseRequestItemBase(product_id=1, quantity=10, estimated_unit_cost=0)
    ]
    with pytest.raises(NotFoundException):
        await PurchaseRequestService.create_draft_request(
            db=seeded_db_session,
            supplier_id=99999,
            items=items,
        )


@pytest.mark.asyncio
async def test_get_purchase_request_by_number(seeded_db_session):
    items = [
        PurchaseRequestItemBase(product_id=1, quantity=10, estimated_unit_cost=0)
    ]
    created = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=1,
        items=items,
    )

    fetched = await PurchaseRequestService.get_request_by_number(
        db=seeded_db_session,
        request_number=created.request_number,
    )
    assert fetched.id == created.id
    assert fetched.total_estimated_cost == Decimal("30.00")
