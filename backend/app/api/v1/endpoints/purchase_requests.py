import math
from typing import Optional
from fastapi import APIRouter, Query, status
from app.api.deps import DBSessionDep, PaginationDep
from app.db.models.purchase_request import PurchaseRequestStatus
from app.schemas.common import PaginatedResponse
from app.schemas.purchase_request import (
    PurchaseRequestCreate,
    PurchaseRequestResponse,
)
from app.services.purchase_request_service import PurchaseRequestService

router = APIRouter(prefix="/purchase-requests", tags=["Purchase Requests"])


@router.get("", response_model=PaginatedResponse[PurchaseRequestResponse])
async def list_purchase_requests(
    db: DBSessionDep,
    pagination: PaginationDep,
    status_filter: Optional[PurchaseRequestStatus] = Query(None, alias="status"),
    supplier_id: Optional[int] = Query(None),
):
    """List purchase requests with optional status and supplier filters."""
    requests, total = await PurchaseRequestService.list_purchase_requests(
        db=db,
        status=status_filter,
        supplier_id=supplier_id,
        page=pagination.page,
        size=pagination.size,
    )
    pages = math.ceil(total / pagination.size) if total > 0 else 1

    return PaginatedResponse[PurchaseRequestResponse](
        items=requests,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get("/{request_id}", response_model=PurchaseRequestResponse)
async def get_purchase_request(request_id: int, db: DBSessionDep):
    """Retrieve purchase request details by ID."""
    return await PurchaseRequestService.get_request_by_id(db=db, request_id=request_id)


@router.post("", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_request(payload: PurchaseRequestCreate, db: DBSessionDep):
    """Create a new draft purchase request."""
    return await PurchaseRequestService.create_draft_request(
        db=db,
        supplier_id=payload.supplier_id,
        items=payload.items,
        priority=payload.priority,
        reason=payload.reason,
    )
