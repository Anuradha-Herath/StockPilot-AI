import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, async_engine
from app.db.base import Base
from app.db.models import (
    User,
    UserRole,
    Product,
    Supplier,
    SupplierProduct,
    InventoryLevel,
    AuditLog,
    ActorType,
)


async def seed_database(db: AsyncSession) -> None:
    # 1. Check if already seeded
    existing_product = (await db.execute(select(Product))).first()
    if existing_product:
        print("Database already contains product data. Skipping seed.")
        return

    print("Seeding initial supermarket domain data...")

    # 2. Seed Users
    users = [
        User(
            email="admin@freshmarket.com",
            username="admin",
            full_name="System Administrator",
            hashed_password="pbkdf2_sha256$mock_admin_hash",
            role=UserRole.ADMIN,
        ),
        User(
            email="sarah.procurement@freshmarket.com",
            username="sarah_manager",
            full_name="Sarah Jenkins (Procurement Manager)",
            hashed_password="pbkdf2_sha256$mock_manager_hash",
            role=UserRole.MANAGER,
        ),
        User(
            email="mike.ops@freshmarket.com",
            username="mike_ops",
            full_name="Mike Miller (Inventory Operator)",
            hashed_password="pbkdf2_sha256$mock_operator_hash",
            role=UserRole.OPERATOR,
        ),
    ]
    db.add_all(users)
    await db.flush()

    # 3. Seed Suppliers (6 distinct suppliers)
    suppliers = [
        Supplier(
            code="SUP-DAIRY-01",
            name="DairyFresh Farms Co.",
            contact_person="Clara Oswald",
            email="orders@dairyfresh.com",
            phone="+1-555-0101",
            address="102 Pasture Way, Green Valley, CA",
            lead_time_days=2,
            rating=Decimal("4.80"),
        ),
        Supplier(
            code="SUP-PRODUCE-02",
            name="GreenValley Organics",
            contact_person="Arthur Pendelton",
            email="wholesale@greenvalley.com",
            phone="+1-555-0102",
            address="55 Orchard Road, Salinas, CA",
            lead_time_days=1,
            rating=Decimal("4.65"),
        ),
        Supplier(
            code="SUP-BEV-03",
            name="BeverageHub Distribution",
            contact_person="Marcus Vance",
            email="supply@beveragehub.com",
            phone="+1-555-0103",
            address="780 Logistics Blvd, Reno, NV",
            lead_time_days=4,
            rating=Decimal("4.30"),
        ),
        Supplier(
            code="SUP-BAKE-04",
            name="GoldenGrain Mill & Bakery",
            contact_person="Hannah Abbott",
            email="sales@goldengrain.com",
            phone="+1-555-0104",
            address="12 Mill Creek Lane, Portland, OR",
            lead_time_days=2,
            rating=Decimal("4.75"),
        ),
        Supplier(
            code="SUP-CLEAN-05",
            name="CleanHome Essentials Inc.",
            contact_person="Derek Shepherd",
            email="orders@cleanhome.com",
            phone="+1-555-0105",
            address="900 Industrial Pkwy, Chicago, IL",
            lead_time_days=5,
            rating=Decimal("4.40"),
        ),
        Supplier(
            code="SUP-MEAT-06",
            name="OceanCatch & Butcher Wholesale",
            contact_person="Gregory House",
            email="orders@oceancatch.com",
            phone="+1-555-0106",
            address="33 Harbor Pier, Seattle, WA",
            lead_time_days=2,
            rating=Decimal("4.90"),
        ),
    ]
    db.add_all(suppliers)
    await db.flush()

    # Map supplier codes to objects for quick reference
    sup_map = {s.code: s for s in suppliers}

    # 4. Seed Products & Inventory Levels (25 Supermarket Items)
    # Format: (sku, name, category, unit, unit_price, current_stock, reorder_point, reorder_qty, max_stock, location, supplier_code, unit_cost, min_order_qty)
    product_catalog = [
        # Dairy & Eggs
        ("SKU-MILK-001", "Whole Milk 1 Gallon", "Dairy", "gallon", Decimal("4.29"), 8, 20, 50, 100, "AISLE-01-A", "SUP-DAIRY-01", Decimal("2.80"), 20),
        ("SKU-EGGS-002", "Organic Pasture-Raised Eggs 12ct", "Dairy", "carton", Decimal("5.49"), 12, 25, 60, 120, "AISLE-01-B", "SUP-DAIRY-01", Decimal("3.20"), 30),
        ("SKU-YOGT-003", "Greek Yogurt Plain 32oz", "Dairy", "tub", Decimal("4.99"), 35, 15, 30, 80, "AISLE-01-C", "SUP-DAIRY-01", Decimal("3.10"), 15),
        ("SKU-CHED-004", "Sharp Cheddar Cheese Block 8oz", "Dairy", "block", Decimal("3.89"), 42, 20, 40, 90, "AISLE-01-D", "SUP-DAIRY-01", Decimal("2.40"), 20),
        ("SKU-BUTR-005", "Unsalted Sweet Butter 16oz", "Dairy", "pack", Decimal("4.79"), 28, 15, 30, 75, "AISLE-01-E", "SUP-DAIRY-01", Decimal("2.95"), 15),

        # Produce (Fruits & Vegetables)
        ("SKU-BANA-006", "Organic Cavendish Bananas", "Produce", "bunch", Decimal("1.99"), 10, 30, 80, 150, "AISLE-02-A", "SUP-PRODUCE-02", Decimal("0.90"), 40),
        ("SKU-APPL-007", "Honeycrisp Apples 3lb Bag", "Produce", "bag", Decimal("5.99"), 45, 20, 40, 100, "AISLE-02-B", "SUP-PRODUCE-02", Decimal("3.40"), 20),
        ("SKU-AVOC-008", "Hass Avocados 4pk", "Produce", "pack", Decimal("4.49"), 0, 15, 40, 80, "AISLE-02-C", "SUP-PRODUCE-02", Decimal("2.50"), 20), # Out of Stock!
        ("SKU-SPIN-009", "Baby Spinach Clamshell 16oz", "Produce", "pack", Decimal("3.99"), 6, 18, 36, 72, "AISLE-02-D", "SUP-PRODUCE-02", Decimal("2.10"), 18),
        ("SKU-TOMA-010", "Roma Tomatoes 1lb", "Produce", "lb", Decimal("2.29"), 50, 20, 50, 120, "AISLE-02-E", "SUP-PRODUCE-02", Decimal("1.15"), 25),

        # Beverages
        ("SKU-OJUC-011", "Fresh Squeezed Orange Juice 52oz", "Beverages", "bottle", Decimal("4.99"), 5, 20, 40, 80, "AISLE-03-A", "SUP-BEV-03", Decimal("3.00"), 20),
        ("SKU-COFF-012", "Dark Roast Ground Coffee 12oz", "Beverages", "bag", Decimal("9.99"), 38, 15, 30, 75, "AISLE-03-B", "SUP-BEV-03", Decimal("6.20"), 10),
        ("SKU-SPRK-013", "Sparkling Spring Water 12-Pack", "Beverages", "case", Decimal("6.49"), 0, 25, 50, 100, "AISLE-03-C", "SUP-BEV-03", Decimal("3.80"), 25), # Out of Stock!
        ("SKU-ALMD-014", "Unsweetened Almond Milk 64oz", "Beverages", "carton", Decimal("3.79"), 24, 15, 30, 60, "AISLE-03-D", "SUP-BEV-03", Decimal("2.20"), 15),
        ("SKU-GTEA-015", "Organic Green Tea Bags 40ct", "Beverages", "box", Decimal("4.29"), 60, 20, 40, 100, "AISLE-03-E", "SUP-BEV-03", Decimal("2.40"), 20),

        # Bakery & Grains
        ("SKU-BRD-016", "Artisan Whole Wheat Sliced Bread", "Bakery", "loaf", Decimal("3.69"), 7, 25, 50, 90, "AISLE-04-A", "SUP-BAKE-04", Decimal("1.90"), 25),
        ("SKU-BAGL-017", "Plain New York Bagels 6ct", "Bakery", "pack", Decimal("3.99"), 30, 15, 30, 60, "AISLE-04-B", "SUP-BAKE-04", Decimal("2.10"), 15),
        ("SKU-OATS-018", "Rolled Rolled Oats 32oz Canister", "Bakery", "canister", Decimal("4.19"), 45, 15, 30, 80, "AISLE-04-C", "SUP-BAKE-04", Decimal("2.30"), 15),
        ("SKU-PSTA-019", "Italian Penne Rigate Pasta 16oz", "Pantry", "box", Decimal("1.89"), 85, 30, 60, 150, "AISLE-04-D", "SUP-BAKE-04", Decimal("0.95"), 30),
        ("SKU-OLIV-020", "Extra Virgin Olive Oil 750ml", "Pantry", "bottle", Decimal("12.99"), 9, 20, 30, 60, "AISLE-04-E", "SUP-BAKE-04", Decimal("7.80"), 10),

        # Meat & Seafood
        ("SKU-CHIK-021", "Boneless Skinless Chicken Breast 2lb", "Meat", "pack", Decimal("8.99"), 11, 25, 50, 100, "AISLE-05-A", "SUP-MEAT-06", Decimal("5.20"), 20),
        ("SKU-BEEF-022", "Grass-Fed Ground Beef 85/15 1lb", "Meat", "pack", Decimal("6.99"), 28, 20, 40, 80, "AISLE-05-B", "SUP-MEAT-06", Decimal("4.10"), 20),
        ("SKU-SALM-023", "Atlantic Salmon Fillets 1lb", "Seafood", "pack", Decimal("11.99"), 18, 15, 30, 50, "AISLE-05-C", "SUP-MEAT-06", Decimal("7.50"), 15),

        # Household & Cleaning
        ("SKU-PTWL-024", "Ultra Absorbent Paper Towels 6ct", "Household", "pack", Decimal("10.49"), 8, 20, 40, 80, "AISLE-06-A", "SUP-CLEAN-05", Decimal("6.10"), 20),
        ("SKU-DISH-025", "Eco Dishwashing Liquid 24oz", "Household", "bottle", Decimal("3.49"), 55, 15, 30, 90, "AISLE-06-B", "SUP-CLEAN-05", Decimal("1.85"), 15),
    ]

    now = datetime.now(timezone.utc)

    for (
        sku,
        name,
        category,
        unit,
        unit_price,
        stock,
        reorder_pt,
        reorder_qty,
        max_stk,
        loc,
        sup_code,
        cost,
        moq,
    ) in product_catalog:
        # Create product
        prod = Product(
            sku=sku,
            name=name,
            description=f"Fresh quality {name.lower()} for supermarket retail.",
            category=category,
            unit=unit,
            unit_price=unit_price,
            is_active=True,
        )
        db.add(prod)
        await db.flush()

        # Create inventory level
        inv = InventoryLevel(
            product_id=prod.id,
            current_stock=stock,
            reserved_stock=2 if stock > 10 else 0,
            reorder_point=reorder_pt,
            reorder_quantity=reorder_qty,
            max_stock=max_stk,
            warehouse_location=loc,
            last_restocked_at=now,
        )
        db.add(inv)

        # Create primary supplier relationship
        supplier = sup_map[sup_code]
        sup_prod = SupplierProduct(
            supplier_id=supplier.id,
            product_id=prod.id,
            supplier_sku=f"VEND-{sku}",
            unit_cost=cost,
            min_order_qty=moq,
            lead_time_days=supplier.lead_time_days,
            is_preferred=True,
        )
        db.add(sup_prod)

    # 5. Create Audit log
    audit_entry = AuditLog(
        actor_type=ActorType.SYSTEM,
        actor_id="system_seeder",
        action="DATABASE_INITIAL_SEED",
        entity_type="Database",
        entity_id="all",
        payload_after={"total_products": len(product_catalog), "total_suppliers": len(suppliers)},
        description="Initial seed completed with 25 products, 6 suppliers, and baseline inventory levels.",
    )
    db.add(audit_entry)

    await db.commit()
    print(f"Successfully seeded {len(product_catalog)} products and {len(suppliers)} suppliers!")


async def run_seed():
    # Helper for running seed script directly
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_database(session)


if __name__ == "__main__":
    asyncio.run(run_seed())
