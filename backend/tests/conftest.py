import asyncio
from decimal import Decimal
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Force testing environment for checkpointer and mocks
settings.ENVIRONMENT = "testing"

from app.core.database import get_db
from app.db.base import Base
from app.db.models import (
    User,
    UserRole,
    Product,
    Supplier,
    SupplierProduct,
    InventoryLevel,
)
from app.main import create_application

# In-memory SQLite async test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database schema for each test and roll it back."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def seeded_db_session(db_session: AsyncSession) -> AsyncSession:
    """Pre-seed sample products and suppliers for integration tests."""
    # 1. Supplier
    supplier1 = Supplier(
        code="TEST-SUP-01",
        name="Test Dairy Co.",
        email="test@dairy.com",
        lead_time_days=2,
        rating=Decimal("4.50"),
    )
    supplier2 = Supplier(
        code="TEST-SUP-02",
        name="Test Bakery Supply",
        email="test@bakery.com",
        lead_time_days=3,
        rating=Decimal("4.80"),
    )
    db_session.add_all([supplier1, supplier2])
    await db_session.flush()

    # 2. Products + Inventory
    # Low stock item
    p1 = Product(
        sku="TEST-SKU-MILK",
        name="Whole Milk Test",
        category="Dairy",
        unit="gallon",
        unit_price=Decimal("4.50"),
    )
    # Healthy stock item
    p2 = Product(
        sku="TEST-SKU-BREAD",
        name="Artisan Bread Test",
        category="Bakery",
        unit="loaf",
        unit_price=Decimal("3.50"),
    )
    db_session.add_all([p1, p2])
    await db_session.flush()

    inv1 = InventoryLevel(
        product_id=p1.id,
        current_stock=5,
        reorder_point=20,
        reorder_quantity=50,
        max_stock=100,
        warehouse_location="AISLE-01",
    )
    inv2 = InventoryLevel(
        product_id=p2.id,
        current_stock=40,
        reorder_point=15,
        reorder_quantity=30,
        max_stock=80,
        warehouse_location="AISLE-02",
    )
    db_session.add_all([inv1, inv2])

    sp1 = SupplierProduct(
        supplier_id=supplier1.id,
        product_id=p1.id,
        unit_cost=Decimal("3.00"),
        min_order_qty=10,
        is_preferred=True,
    )
    db_session.add(sp1)

    await db_session.commit()
    return db_session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client using the test database session dependency."""
    app = create_application()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()
