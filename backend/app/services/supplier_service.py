from typing import Optional, Tuple, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.supplier import Supplier
from app.db.models.supplier_product import SupplierProduct
from app.schemas.supplier import (
    SupplierCreate,
    SupplierDetailResponse,
    SupplierProductItem,
    SupplierResponse,
    SupplierUpdate,
)


class SupplierService:
    @staticmethod
    async def get_suppliers(
        db: AsyncSession,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[SupplierResponse], int]:
        query = select(
            Supplier,
            func.count(SupplierProduct.id).label("total_products"),
        ).outerjoin(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)

        if search:
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (Supplier.name.ilike(search_filter))
                | (Supplier.code.ilike(search_filter))
                | (Supplier.email.ilike(search_filter))
            )

        query = query.group_by(Supplier.id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        paginated_query = query.order_by(Supplier.name.asc()).offset(offset).limit(size)
        result = await db.execute(paginated_query)
        rows = result.all()

        supplier_responses = []
        for supplier, total_products in rows:
            resp = SupplierResponse.model_validate(supplier)
            resp.total_products_count = total_products
            supplier_responses.append(resp)

        return supplier_responses, total

    @staticmethod
    async def get_supplier_by_id(db: AsyncSession, supplier_id: int) -> SupplierDetailResponse:
        query = (
            select(Supplier)
            .where(Supplier.id == supplier_id)
            .options(
                selectinload(Supplier.supplier_products).joinedload(SupplierProduct.product)
            )
        )
        result = await db.execute(query)
        supplier = result.scalar_one_or_none()

        if not supplier:
            raise NotFoundException("Supplier", supplier_id)

        supplied_products = [
            SupplierProductItem(
                product_id=sp.product_id,
                product_sku=sp.product.sku,
                product_name=sp.product.name,
                product_category=sp.product.category,
                supplier_sku=sp.supplier_sku,
                unit_cost=sp.unit_cost,
                min_order_qty=sp.min_order_qty,
                lead_time_days=sp.lead_time_days or supplier.lead_time_days,
                is_preferred=sp.is_preferred,
            )
            for sp in supplier.supplier_products
        ]

        resp = SupplierDetailResponse.model_validate(supplier)
        resp.total_products_count = len(supplied_products)
        resp.supplied_products = supplied_products
        return resp

    @staticmethod
    async def create_supplier(db: AsyncSession, payload: SupplierCreate) -> Supplier:
        code_query = select(Supplier).where(Supplier.code == payload.code)
        existing = (await db.execute(code_query)).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Supplier with code '{payload.code}' already exists.")

        supplier = Supplier(
            code=payload.code,
            name=payload.name,
            contact_person=payload.contact_person,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            lead_time_days=payload.lead_time_days,
            rating=payload.rating,
            is_active=payload.is_active,
        )
        db.add(supplier)
        await db.commit()
        await db.refresh(supplier)
        return supplier
