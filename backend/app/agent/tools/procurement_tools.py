from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import ToolResult, safe_tool_executor
from app.agent.tools.schemas import (
    CreateDraftPurchaseRequestInput,
    CreateDraftPurchaseRequestOutput,
    GetPurchaseRequestStatusInput,
    GetPurchaseRequestStatusOutput,
    PurchaseRequestLineItemSummary,
)
from app.core.exceptions import BadRequestException
from app.db.models.audit_log import ActorType
from app.schemas.purchase_request import PurchaseRequestItemBase
from app.services.purchase_request_service import PurchaseRequestService


@safe_tool_executor("create_draft_purchase_request")
async def create_draft_purchase_request(
    db: AsyncSession,
    args: CreateDraftPurchaseRequestInput,
) -> ToolResult[CreateDraftPurchaseRequestOutput]:
    """
    Creates a draft purchase request for review by procurement managers.
    Validates supplier ID, product IDs, minimum order quantities, and contract pricing.
    NOTE: This does NOT submit a purchase order or spend budget. Status is strictly DRAFT.
    """
    domain_items = [
        PurchaseRequestItemBase(
            product_id=item.product_id,
            quantity=item.quantity,
            estimated_unit_cost=0,  # Will be populated from supplier_product record in service
        )
        for item in args.items
    ]

    pr_response = await PurchaseRequestService.create_draft_request(
        db=db,
        supplier_id=args.supplier_id,
        items=domain_items,
        priority=args.priority,
        reason=args.reason,
        actor_type=ActorType.AI_AGENT,
        actor_id="langgraph_copilot_tool",
    )

    line_summaries = [
        PurchaseRequestLineItemSummary(
            id=item.id,
            product_id=item.product_id,
            product_sku=item.product_sku,
            product_name=item.product_name,
            quantity=item.quantity,
            estimated_unit_cost=item.estimated_unit_cost,
            total_cost=item.total_cost,
        )
        for item in pr_response.items
    ]

    return ToolResult.ok(
        CreateDraftPurchaseRequestOutput(
            id=pr_response.id,
            request_number=pr_response.request_number,
            supplier_id=pr_response.supplier_id,
            supplier_name=pr_response.supplier_name or "Unknown Supplier",
            status=pr_response.status,
            priority=pr_response.priority,
            reason=pr_response.reason,
            total_estimated_cost=pr_response.total_estimated_cost,
            items=line_summaries,
            created_at=pr_response.created_at.isoformat(),
            next_step="Proposal registered in DRAFT state. Awaiting manager approval before PO issuance.",
        )
    )


@safe_tool_executor("get_purchase_request_status")
async def get_purchase_request_status(
    db: AsyncSession,
    args: GetPurchaseRequestStatusInput,
) -> ToolResult[GetPurchaseRequestStatusOutput]:
    """
    Checks the real-time status and details of a Purchase Request.
    Lookup can be performed using either request_number (e.g. 'PR-20260919-AB12') or request_id.
    """
    if args.request_number:
        pr_response = await PurchaseRequestService.get_request_by_number(
            db=db, request_number=args.request_number
        )
    elif args.request_id:
        pr_response = await PurchaseRequestService.get_request_by_id(
            db=db, request_id=args.request_id
        )
    else:
        raise BadRequestException("Must provide either 'request_number' or 'request_id'.")

    line_summaries = [
        PurchaseRequestLineItemSummary(
            id=item.id,
            product_id=item.product_id,
            product_sku=item.product_sku,
            product_name=item.product_name,
            quantity=item.quantity,
            estimated_unit_cost=item.estimated_unit_cost,
            total_cost=item.total_cost,
        )
        for item in pr_response.items
    ]

    return ToolResult.ok(
        GetPurchaseRequestStatusOutput(
            id=pr_response.id,
            request_number=pr_response.request_number,
            supplier_id=pr_response.supplier_id,
            supplier_name=pr_response.supplier_name or "Unknown Supplier",
            status=pr_response.status,
            priority=pr_response.priority,
            total_estimated_cost=pr_response.total_estimated_cost,
            item_count=len(line_summaries),
            items=line_summaries,
            created_at=pr_response.created_at.isoformat(),
        )
    )
