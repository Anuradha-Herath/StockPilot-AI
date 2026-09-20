import math
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import DBSessionDep, PaginationDep
from app.schemas.common import PaginatedResponse
from app.schemas.supplier import (
    SupplierCreate,
    SupplierDetailResponse,
    SupplierResponse,
)
from app.services.supplier_service import SupplierService

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_suppliers(
    db: DBSessionDep,
    pagination: PaginationDep,
    search: Optional[str] = Query(None, description="Search term for code, name or email"),
):
    """List registered suppliers with total products supplied count."""
    suppliers, total = await SupplierService.get_suppliers(
        db=db,
        search=search,
        page=pagination.page,
        size=pagination.size,
    )
    pages = math.ceil(total / pagination.size) if total > 0 else 1

    return PaginatedResponse[SupplierResponse](
        items=suppliers,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get("/{supplier_id}", response_model=SupplierDetailResponse)
async def get_supplier(supplier_id: int, db: DBSessionDep):
    """Retrieve supplier details including their product catalog, unit costs, and lead times."""
    return await SupplierService.get_supplier_by_id(db=db, supplier_id=supplier_id)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(payload: SupplierCreate, db: DBSessionDep):
    """Register a new supplier."""
    supplier = await SupplierService.create_supplier(db=db, payload=payload)
    resp = SupplierResponse.model_validate(supplier)
    resp.total_products_count = 0
    return resp
