import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.exceptions import BadRequestException, NotFoundException
from app.db.models.audit_log import ActorType, AuditLog
from app.db.models.product import Product
from app.db.models.purchase_request import (
    PriorityLevel,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseRequestStatus,
)
from app.db.models.supplier import Supplier
from app.db.models.supplier_product import SupplierProduct
from app.schemas.purchase_request import (
    PurchaseRequestCreate,
    PurchaseRequestItemBase,
    PurchaseRequestResponse,
    PurchaseRequestItemResponse,
)


class PurchaseRequestService:
    @staticmethod
    def generate_request_number() -> str:
        """Generate a standard formatted Purchase Request Number e.g. PR-20260919-AB12."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"PR-{now_str}-{short_id}"

    @staticmethod
    async def create_draft_request(
        db: AsyncSession,
        supplier_id: int,
        items: List[PurchaseRequestItemBase],
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        reason: Optional[str] = None,
        requester_id: Optional[int] = None,
        actor_type: ActorType = ActorType.AI_AGENT,
        actor_id: Optional[str] = "agent_procurement_tool",
    ) -> PurchaseRequestResponse:
        """
        Creates a DRAFT Purchase Request with strict business validations:
        - Supplier must exist and be active.
        - Items must not be empty.
        - Product IDs must be unique within the request.
        - Each product must exist, be active, and be supplied by the chosen supplier.
        - Unit costs are loaded from verified supplier-product records.
        - Request is saved with status DRAFT (cannot commit financial orders).
        - Creates an immutable audit record.
        """
        if not items:
            raise BadRequestException("Purchase request must contain at least one item.")

        # 1. Validate Supplier
        sup_query = select(Supplier).where(Supplier.id == supplier_id)
        supplier = (await db.execute(sup_query)).scalar_one_or_none()
        if not supplier:
            raise NotFoundException("Supplier", supplier_id)
        if not supplier.is_active:
            raise BadRequestException(f"Supplier '{supplier.name}' (ID: {supplier_id}) is currently inactive.")

        # 2. Check for Duplicate Products in the same request
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise BadRequestException("Duplicate products detected in request items. Each SKU must appear only once.")

        # 3. Validate Products and Supplier-Product Associations
        sp_query = (
            select(SupplierProduct)
            .where(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.product_id.in_(product_ids),
            )
            .options(joinedload(SupplierProduct.product))
        )
        sp_results = (await db.execute(sp_query)).scalars().all()
        sp_map = {sp.product_id: sp for sp in sp_results}

        # Check for missing associations
        missing_pids = set(product_ids) - set(sp_map.keys())
        if missing_pids:
            # Check if products exist at all to give precise error
            p_query = select(Product).where(Product.id.in_(list(missing_pids)))
            found_products = (await db.execute(p_query)).scalars().all()
            found_map = {p.id: p for p in found_products}

            unsupplied = []
            for pid in missing_pids:
                if pid in found_map:
                    unsupplied.append(f"Product '{found_map[pid].name}' (ID: {pid}) is not supplied by {supplier.name}")
                else:
                    unsupplied.append(f"Product ID {pid} does not exist in catalog")

            raise BadRequestException(
                f"Validation failed for request items: {'; '.join(unsupplied)}."
            )

        # 4. Build Purchase Request and Items
        request_number = PurchaseRequestService.generate_request_number()
        total_estimated_cost = Decimal("0.00")
        db_items = []

        for item_input in items:
            if item_input.quantity < 1:
                raise BadRequestException(f"Quantity for product ID {item_input.product_id} must be at least 1.")

            sp = sp_map[item_input.product_id]
            unit_cost = sp.unit_cost
            line_total = Decimal(str(item_input.quantity)) * unit_cost
            total_estimated_cost += line_total

            db_items.append(
                PurchaseRequestItem(
                    product_id=sp.product_id,
                    quantity=item_input.quantity,
                    estimated_unit_cost=unit_cost,
                    total_cost=line_total,
                )
            )

        # Create Header
        purchase_request = PurchaseRequest(
            request_number=request_number,
            requester_id=requester_id,
            supplier_id=supplier_id,
            status=PurchaseRequestStatus.DRAFT,  # Strictly DRAFT
            priority=priority,
            reason=reason or "Automated replenishment proposal generated for review.",
            total_estimated_cost=total_estimated_cost,
            items=db_items,
        )

        db.add(purchase_request)
        await db.flush()  # Populates purchase_request.id and items.id

        # 5. Record Audit Log
        audit = AuditLog(
            actor_type=actor_type,
            actor_id=str(actor_id or requester_id or "system"),
            action="CREATE_DRAFT_PURCHASE_REQUEST",
            entity_type="PurchaseRequest",
            entity_id=str(purchase_request.id),
            payload_after={
                "request_number": request_number,
                "supplier_id": supplier_id,
                "supplier_name": supplier.name,
                "total_estimated_cost": str(total_estimated_cost),
                "item_count": len(db_items),
                "status": PurchaseRequestStatus.DRAFT.value,
            },
            description=f"Created draft purchase request {request_number} with {len(db_items)} items.",
        )
        db.add(audit)

        await db.commit()

        # Re-fetch with relationships for clean response
        return await PurchaseRequestService.get_request_by_id(db, purchase_request.id)

    @staticmethod
    async def get_request_by_id(db: AsyncSession, request_id: int) -> PurchaseRequestResponse:
        """Retrieve full details of a purchase request by ID."""
        query = (
            select(PurchaseRequest)
            .where(PurchaseRequest.id == request_id)
            .options(
                joinedload(PurchaseRequest.supplier),
                selectinload(PurchaseRequest.items).joinedload(PurchaseRequestItem.product),
            )
        )
        result = await db.execute(query)
        req = result.scalar_one_or_none()

        if not req:
            raise NotFoundException("PurchaseRequest", request_id)

        return PurchaseRequestService._build_response(req)

    @staticmethod
    async def get_request_by_number(db: AsyncSession, request_number: str) -> PurchaseRequestResponse:
        """Retrieve full details of a purchase request by request_number."""
        query = (
            select(PurchaseRequest)
            .where(PurchaseRequest.request_number == request_number.strip().upper())
            .options(
                joinedload(PurchaseRequest.supplier),
                selectinload(PurchaseRequest.items).joinedload(PurchaseRequestItem.product),
            )
        )
        result = await db.execute(query)
        req = result.scalar_one_or_none()

        if not req:
            raise NotFoundException("PurchaseRequest Number", request_number)

        return PurchaseRequestService._build_response(req)

    @staticmethod
    async def list_purchase_requests(
        db: AsyncSession,
        status: Optional[PurchaseRequestStatus] = None,
        supplier_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[PurchaseRequestResponse], int]:
        """List purchase requests with optional status and supplier filtering."""
        query = (
            select(PurchaseRequest)
            .options(
                joinedload(PurchaseRequest.supplier),
                selectinload(PurchaseRequest.items).joinedload(PurchaseRequestItem.product),
            )
        )

        if status is not None:
            query = query.where(PurchaseRequest.status == status)

        if supplier_id is not None:
            query = query.where(PurchaseRequest.supplier_id == supplier_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        offset = (page - 1) * size
        paginated_query = query.order_by(PurchaseRequest.created_at.desc()).offset(offset).limit(size)
        result = await db.execute(paginated_query)
        requests = result.scalars().all()

        return [PurchaseRequestService._build_response(r) for r in requests], total

    @staticmethod
    def _build_response(req: PurchaseRequest) -> PurchaseRequestResponse:
        items_resp = [
            PurchaseRequestItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_sku=item.product.sku if item.product else None,
                product_name=item.product.name if item.product else None,
                quantity=item.quantity,
                estimated_unit_cost=item.estimated_unit_cost,
                total_cost=item.total_cost,
            )
            for item in req.items
        ]

        return PurchaseRequestResponse(
            id=req.id,
            request_number=req.request_number,
            requester_id=req.requester_id,
            supplier_id=req.supplier_id,
            supplier_name=req.supplier.name if req.supplier else None,
            status=req.status,
            priority=req.priority,
            reason=req.reason,
            total_estimated_cost=req.total_estimated_cost,
            items=items_resp,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )
