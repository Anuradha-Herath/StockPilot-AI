from typing import Optional, Tuple, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.product import Product
from app.db.models.inventory import InventoryLevel
from app.db.models.supplier_product import SupplierProduct
from app.schemas.product import ProductCreate, ProductDetailResponse, ProductResponse, ProductSupplierInfo, ProductUpdate


class ProductService:
    @staticmethod
    async def get_products(
        db: AsyncSession,
        search: Optional[str] = None,
        category: Optional[str] = None,
        low_stock_only: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Product], int]:
        query = select(Product).options(selectinload(Product.inventory))

        if search:
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (Product.name.ilike(search_filter))
                | (Product.sku.ilike(search_filter))
                | (Product.category.ilike(search_filter))
            )

        if category:
            query = query.where(Product.category.ilike(category.strip()))

        if low_stock_only:
            query = query.join(Product.inventory).where(
                InventoryLevel.current_stock <= InventoryLevel.reorder_point
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Pagination
        offset = (page - 1) * size
        paginated_query = query.order_by(Product.name.asc()).offset(offset).limit(size)
        result = await db.execute(paginated_query)
        products = list(result.scalars().all())

        return products, total

    @staticmethod
    async def get_product_by_id(db: AsyncSession, product_id: int) -> ProductDetailResponse:
        query = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.inventory),
                selectinload(Product.supplier_products).joinedload(SupplierProduct.supplier),
            )
        )
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise NotFoundException("Product", product_id)

        suppliers_info = [
            ProductSupplierInfo(
                supplier_id=sp.supplier_id,
                supplier_name=sp.supplier.name,
                supplier_code=sp.supplier.code,
                supplier_sku=sp.supplier_sku,
                unit_cost=sp.unit_cost,
                min_order_qty=sp.min_order_qty,
                lead_time_days=sp.lead_time_days or sp.supplier.lead_time_days,
                is_preferred=sp.is_preferred,
            )
            for sp in product.supplier_products
        ]

        return ProductDetailResponse(
            id=product.id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            category=product.category,
            unit=product.unit,
            unit_price=product.unit_price,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
            inventory=product.inventory,
            suppliers=suppliers_info,
        )

    @staticmethod
    async def create_product(db: AsyncSession, payload: ProductCreate) -> Product:
        # Check SKU uniqueness
        sku_query = select(Product).where(Product.sku == payload.sku)
        existing = (await db.execute(sku_query)).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Product with SKU '{payload.sku}' already exists.")

        product = Product(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            unit=payload.unit,
            unit_price=payload.unit_price,
            is_active=payload.is_active,
        )
        db.add(product)
        await db.flush()  # To populate product.id

        inventory = InventoryLevel(
            product_id=product.id,
            current_stock=payload.initial_stock,
            reorder_point=payload.reorder_point,
            reorder_quantity=payload.reorder_quantity,
            max_stock=payload.max_stock,
            warehouse_location=payload.warehouse_location,
        )
        db.add(inventory)
        await db.commit()
        await db.refresh(product, ["inventory"])
        return product
