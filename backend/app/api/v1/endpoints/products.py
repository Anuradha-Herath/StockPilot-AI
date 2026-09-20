import math
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import DBSessionDep, PaginationDep
from app.schemas.common import PaginatedResponse
from app.schemas.product import ProductCreate, ProductDetailResponse, ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    db: DBSessionDep,
    pagination: PaginationDep,
    search: Optional[str] = Query(None, description="Search term for SKU, name or category"),
    category: Optional[str] = Query(None, description="Filter by exact category name"),
    low_stock_only: bool = Query(False, description="Filter only products with stock <= reorder point"),
):
    """List products with pagination, search, and low-stock filtering."""
    products, total = await ProductService.get_products(
        db=db,
        search=search,
        category=category,
        low_stock_only=low_stock_only,
        page=pagination.page,
        size=pagination.size,
    )
    pages = math.ceil(total / pagination.size) if total > 0 else 1

    return PaginatedResponse[ProductResponse](
        items=products,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(product_id: int, db: DBSessionDep):
    """Retrieve product details including live inventory and supplier catalog options."""
    return await ProductService.get_product_by_id(db=db, product_id=product_id)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: DBSessionDep):
    """Create a new product with initial inventory configuration."""
    return await ProductService.create_product(db=db, payload=payload)
