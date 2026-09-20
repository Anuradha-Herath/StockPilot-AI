from decimal import Decimal
import pytest
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.models import Product, InventoryLevel, Supplier, SupplierProduct
from app.services.inventory_service import InventoryService


@pytest.mark.asyncio
async def test_reorder_recommendation_basic(seeded_db_session):
    # Product 1 has current_stock=5, reorder_point=20, max_stock=100.
    # Preferred supplier unit_cost is $3.00, MOQ=10.
    result = await InventoryService.calculate_reorder_recommendation(
        db=seeded_db_session,
        product_id=1,
    )

    assert result["product_id"] == 1
    assert result["is_low_stock"] is True
    assert result["current_stock"] == 5
    assert result["deficit"] == 95  # 100 max - 5 current
    assert result["suggested_order_qty"] == 95
    assert result["unit_cost"] == Decimal("3.00")
    assert result["estimated_total_cost"] == Decimal("285.00")  # 95 * 3.00


@pytest.mark.asyncio
async def test_reorder_recommendation_moq_enforcement(seeded_db_session):
    # Create product with small deficit but high supplier MOQ
    prod = Product(
        sku="SKU-MOQ-TEST",
        name="MOQ Test Item",
        category="Test",
        unit="pack",
        unit_price=Decimal("10.00"),
    )
    seeded_db_session.add(prod)
    await seeded_db_session.flush()

    inv = InventoryLevel(
        product_id=prod.id,
        current_stock=18,
        reorder_point=20,
        reorder_quantity=10,
        max_stock=25,
    )
    seeded_db_session.add(inv)

    sup = Supplier(
        code="SUP-MOQ-01",
        name="Bulk Supplier",
        email="bulk@test.com",
    )
    seeded_db_session.add(sup)
    await seeded_db_session.flush()

    sp = SupplierProduct(
        supplier_id=sup.id,
        product_id=prod.id,
        unit_cost=Decimal("5.00"),
        min_order_qty=50,  # MOQ is 50, but deficit is only 7 (25 - 18)
        is_preferred=True,
    )
    seeded_db_session.add(sp)
    await seeded_db_session.commit()

    result = await InventoryService.calculate_reorder_recommendation(
        db=seeded_db_session,
        product_id=prod.id,
    )

    # Deficit is 7, but suggested_order_qty must be elevated to MOQ (50)
    assert result["deficit"] == 7
    assert result["suggested_order_qty"] == 50
    assert result["estimated_total_cost"] == Decimal("250.00")  # 50 * 5.00


@pytest.mark.asyncio
async def test_reorder_recommendation_custom_target(seeded_db_session):
    # Custom target_stock_level of 60
    result = await InventoryService.calculate_reorder_recommendation(
        db=seeded_db_session,
        product_id=1,
        target_stock_level=60,
    )
    assert result["target_stock_level"] == 60
    assert result["deficit"] == 55  # 60 - 5
    assert result["suggested_order_qty"] == 55
    assert result["estimated_total_cost"] == Decimal("165.00")  # 55 * 3.00


@pytest.mark.asyncio
async def test_reorder_recommendation_invalid_target_below_reorder_point(seeded_db_session):
    # Reorder point is 20; target stock of 10 must be rejected
    with pytest.raises(BadRequestException):
        await InventoryService.calculate_reorder_recommendation(
            db=seeded_db_session,
            product_id=1,
            target_stock_level=10,
        )


@pytest.mark.asyncio
async def test_reorder_recommendation_nonexistent_product(seeded_db_session):
    with pytest.raises(NotFoundException):
        await InventoryService.calculate_reorder_recommendation(
            db=seeded_db_session,
            product_id=99999,
        )
