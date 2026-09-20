from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from app.db.models import (
    Product,
    Supplier,
    SupplierProduct,
    InventoryLevel,
    User,
    UserRole,
)


@pytest.mark.asyncio
async def test_product_and_inventory_properties(db_session):
    prod = Product(
        sku="TEST-PROP-01",
        name="Test Item",
        category="Test Category",
        unit="pack",
        unit_price=Decimal("12.50"),
    )
    db_session.add(prod)
    await db_session.flush()

    inv = InventoryLevel(
        product_id=prod.id,
        current_stock=8,
        reserved_stock=2,
        reorder_point=10,
        reorder_quantity=25,
        max_stock=50,
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    # Test computed properties
    assert inv.available_stock == 6  # 8 current - 2 reserved
    assert inv.is_low_stock is True  # 8 <= 10


@pytest.mark.asyncio
async def test_duplicate_sku_integrity_error(db_session):
    p1 = Product(
        sku="DUPLICATE-SKU",
        name="Product A",
        category="General",
        unit_price=Decimal("5.00"),
    )
    db_session.add(p1)
    await db_session.commit()

    p2 = Product(
        sku="DUPLICATE-SKU",
        name="Product B",
        category="General",
        unit_price=Decimal("10.00"),
    )
    db_session.add(p2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_supplier_unique_code_constraint(db_session):
    s1 = Supplier(
        code="SUPP-UNIQUE",
        name="Supplier 1",
        email="sup1@example.com",
    )
    db_session.add(s1)
    await db_session.commit()

    s2 = Supplier(
        code="SUPP-UNIQUE",
        name="Supplier 2",
        email="sup2@example.com",
    )
    db_session.add(s2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
