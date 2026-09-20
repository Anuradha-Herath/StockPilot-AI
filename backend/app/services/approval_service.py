import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.db.models.approval import ApprovalDecision, ApprovalRecord
from app.db.models.audit_log import ActorType, AuditLog
from app.db.models.product import Product
from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.db.models.purchase_request import (
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseRequestStatus,
)
from app.db.models.supplier import Supplier
from app.db.models.supplier_product import SupplierProduct
from app.db.models.user import User, UserRole
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalRecordResponse,
    OrderExecutionResult,
    PendingApprovalSummary,
)
from app.schemas.purchase_request import (
    PurchaseRequestItemResponse,
    PurchaseRequestResponse,
)
from app.services.procurement_client import MockProcurementClient

logger = logging.getLogger("stockpilot.approval")


class ApprovalService:
    @staticmethod
    def compute_proposal_hash(supplier_id: int, items: List[Tuple[int, int, Decimal]]) -> str:
        """
        Computes a deterministic SHA-256 hash of the proposal contents.
        items: List of (product_id, quantity, unit_cost) tuples.
        """
        # Sort items by product_id to guarantee canonical representation
        sorted_items = sorted(items, key=lambda x: x[0])
        canonical_str = f"supplier:{supplier_id}|items:" + ",".join(
            f"{pid}:{qty}:{str(cost)}" for pid, qty, cost in sorted_items
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    async def submit_for_approval(
        db: AsyncSession,
        request_id: int,
        requester: Optional[User] = None,
    ) -> PurchaseRequestResponse:
        """Transitions a DRAFT purchase request to PENDING_APPROVAL status."""
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

        if req.status != PurchaseRequestStatus.DRAFT:
            raise ConflictException(
                f"Cannot submit request {req.request_number} for approval because it is in status '{req.status.value}'."
            )

        req.status = PurchaseRequestStatus.PENDING_APPROVAL
        if requester and req.requester_id is None:
            req.requester_id = requester.id

        # Record audit log
        audit = AuditLog(
            actor_type=ActorType.USER if requester else ActorType.AI_AGENT,
            actor_id=str(requester.id if requester else "agent_copilot"),
            action="SUBMIT_FOR_APPROVAL",
            entity_type="PurchaseRequest",
            entity_id=str(req.id),
            payload_after={
                "request_number": req.request_number,
                "status": PurchaseRequestStatus.PENDING_APPROVAL.value,
                "total_estimated_cost": str(req.total_estimated_cost),
            },
            description=f"Submitted purchase request {req.request_number} for manager approval.",
        )
        db.add(audit)
        await db.commit()
        from app.services.purchase_request_service import PurchaseRequestService
        return await PurchaseRequestService.get_request_by_id(db, req.id)

    @staticmethod
    async def get_pending_approvals(db: AsyncSession) -> List[PendingApprovalSummary]:
        """List all purchase requests currently pending manager approval."""
        query = (
            select(PurchaseRequest)
            .where(PurchaseRequest.status == PurchaseRequestStatus.PENDING_APPROVAL)
            .options(
                joinedload(PurchaseRequest.supplier),
                joinedload(PurchaseRequest.requester),
                selectinload(PurchaseRequest.items).joinedload(PurchaseRequestItem.product),
            )
            .order_by(PurchaseRequest.created_at.asc())
        )
        result = await db.execute(query)
        requests = result.scalars().all()

        summaries = []
        for req in requests:
            item_tuples = [
                (item.product_id, item.quantity, item.estimated_unit_cost)
                for item in req.items
            ]
            proposal_hash = ApprovalService.compute_proposal_hash(req.supplier_id, item_tuples)

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

            summaries.append(
                PendingApprovalSummary(
                    request_id=req.id,
                    request_number=req.request_number,
                    supplier_id=req.supplier_id,
                    supplier_name=req.supplier.name,
                    requester_id=req.requester_id,
                    requester_name=req.requester.full_name if req.requester else "AI Agent",
                    status=req.status,
                    priority=req.priority,
                    reason=req.reason,
                    total_estimated_cost=req.total_estimated_cost,
                    proposal_version_hash=proposal_hash,
                    items_count=len(items_resp),
                    items=items_resp,
                    created_at=req.created_at,
                )
            )

        return summaries

    @staticmethod
    async def approve_and_create_order(
        db: AsyncSession,
        request_id: int,
        approver: User,
        payload: ApprovalDecisionRequest,
    ) -> OrderExecutionResult:
        """
        Secure Manager Approval & PO Execution:
        1. Enforces Manager/Admin authorization.
        2. Prohibits self-approval (requester cannot approve own request).
        3. Validates proposal state with concurrency row lock.
        4. Revalidates suppliers, products, and pricing against the live database.
        5. Verifies proposal integrity hash (protects against stale or modified proposals).
        6. Atomically creates PurchaseOrder + Items + ApprovalRecord + AuditLog.
        7. Dispatches to MockProcurementClient.
        """
        # 1. Authorization Guard
        if approver.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise AppException(
                message=f"Access Denied: User '{approver.username}' with role '{approver.role.value}' is not authorized to approve purchase orders. Requires MANAGER or ADMIN.",
                status_code=403,
            )

        # 2. Concurrency Lock & State Retrieval
        query = (
            select(PurchaseRequest)
            .where(PurchaseRequest.id == request_id)
            .with_for_update()
            .options(
                selectinload(PurchaseRequest.supplier),
                selectinload(PurchaseRequest.items).selectinload(PurchaseRequestItem.product),
            )
        )
        result = await db.execute(query)
        req = result.scalar_one_or_none()

        if not req:
            raise NotFoundException("PurchaseRequest", request_id)

        # 3. Idempotency Check (prevents duplicate execution on network retries)
        if payload.idempotency_key:
            existing_audit = await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "APPROVE_AND_ISSUE_PURCHASE_ORDER",
                    AuditLog.payload_after["idempotency_key"].as_string() == payload.idempotency_key,
                )
            )
            if existing_audit.first():
                raise ConflictException(
                    f"Duplicate execution prevented. Idempotency key '{payload.idempotency_key}' has already been processed."
                )

        # 4. Prevent Self-Approval (Segregation of Duties)
        if req.requester_id is not None and req.requester_id == approver.id:
            raise AppException(
                message="Security Policy Violation: Requesters are prohibited from approving their own purchase proposals.",
                status_code=403,
            )

        # 5. State Validation
        if req.status != PurchaseRequestStatus.PENDING_APPROVAL:
            raise ConflictException(
                f"Cannot approve request {req.request_number}. Current status is '{req.status.value}', expected 'PENDING_APPROVAL'."
            )

        # 6. Revalidation of Supplier & Products
        supplier = req.supplier
        if not supplier.is_active:
            raise ConflictException(f"Supplier '{supplier.name}' is currently inactive. Order creation aborted.")

        product_ids = [item.product_id for item in req.items]
        sp_query = (
            select(SupplierProduct)
            .where(
                SupplierProduct.supplier_id == req.supplier_id,
                SupplierProduct.product_id.in_(product_ids),
            )
        )
        sp_records = (await db.execute(sp_query)).scalars().all()
        sp_map = {sp.product_id: sp for sp in sp_records}

        if len(sp_map) != len(product_ids):
            raise ConflictException("One or more products in proposal are no longer available from this supplier.")

        # Re-verify prices and compute current hash
        current_item_tuples = []
        for item in req.items:
            current_unit_cost = sp_map[item.product_id].unit_cost
            current_item_tuples.append((item.product_id, item.quantity, current_unit_cost))

        current_hash = ApprovalService.compute_proposal_hash(req.supplier_id, current_item_tuples)

        # 7. Proposal Version Hash Integrity Verification
        if current_hash != payload.proposal_version_hash.strip():
            raise ConflictException(
                "Proposal verification failed: The proposal content or supplier pricing was modified since initial manager review."
            )

        # 8. Atomic Order Creation
        now = datetime.now(timezone.utc)
        po_number = f"PO-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        po_items = []
        total_amount = Decimal("0.00")
        for item in req.items:
            unit_cost = sp_map[item.product_id].unit_cost
            line_total = Decimal(str(item.quantity)) * unit_cost
            total_amount += line_total

            po_items.append(
                PurchaseOrderItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    received_quantity=0,
                )
            )

        purchase_order = PurchaseOrder(
            order_number=po_number,
            supplier_id=req.supplier_id,
            status=PurchaseOrderStatus.ISSUED,
            total_amount=total_amount,
            currency="USD",
            created_by_id=req.requester_id,
            approved_by_id=approver.id,
            approved_at=now,
            notes=f"Converted from Purchase Request {req.request_number}. Approver comments: {payload.comments or 'None'}",
            items=po_items,
        )
        db.add(purchase_order)
        await db.flush()

        # Create Approval Record
        approval_record = ApprovalRecord(
            purchase_request_id=req.id,
            purchase_order_id=purchase_order.id,
            approver_id=approver.id,
            decision=ApprovalDecision.APPROVED,
            comments=payload.comments,
            decision_timestamp=now,
        )
        db.add(approval_record)

        # Update Request Status
        req.status = PurchaseRequestStatus.CONVERTED_TO_PO

        # 9. Mock Transmission to Supplier Endpoint
        tx_receipt = await MockProcurementClient.dispatch_purchase_order(
            supplier_id=supplier.id,
            supplier_code=supplier.code,
            order_number=po_number,
            total_amount=total_amount,
            items=[{"product_id": it.product_id, "quantity": it.quantity} for it in po_items],
        )

        # 10. Audit Ledger Entry
        audit = AuditLog(
            actor_type=ActorType.USER,
            actor_id=str(approver.id),
            action="APPROVE_AND_ISSUE_PURCHASE_ORDER",
            entity_type="PurchaseOrder",
            entity_id=str(purchase_order.id),
            payload_after={
                "order_number": po_number,
                "purchase_request_id": req.id,
                "request_number": req.request_number,
                "supplier_id": supplier.id,
                "total_amount": str(total_amount),
                "approver_id": approver.id,
                "approver_role": approver.role.value,
                "transmission_id": tx_receipt.transmission_id,
                "idempotency_key": payload.idempotency_key,
            },
            description=f"Approved PR {req.request_number} and issued Purchase Order {po_number} to {supplier.name}.",
        )
        db.add(audit)

        await db.commit()

        return OrderExecutionResult(
            purchase_order_id=purchase_order.id,
            order_number=purchase_order.order_number,
            purchase_request_id=req.id,
            request_number=req.request_number,
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            total_amount=total_amount,
            currency="USD",
            status=purchase_order.status.value,
            approved_by_id=approver.id,
            approved_by_name=approver.full_name,
            transmission_id=tx_receipt.transmission_id,
            created_at=now,
        )

    @staticmethod
    async def reject_request(
        db: AsyncSession,
        request_id: int,
        approver: User,
        comments: str,
    ) -> PurchaseRequestResponse:
        """
        Rejects a purchase request.
        Does NOT create a purchase order or mutate inventory.
        """
        # Authorization Guard
        if approver.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise AppException(
                message=f"Access Denied: User '{approver.username}' with role '{approver.role.value}' is not authorized to reject purchase requests.",
                status_code=403,
            )

        query = (
            select(PurchaseRequest)
            .where(PurchaseRequest.id == request_id)
            .with_for_update()
            .options(selectinload(PurchaseRequest.supplier))
        )
        result = await db.execute(query)
        req = result.scalar_one_or_none()

        if not req:
            raise NotFoundException("PurchaseRequest", request_id)

        if req.status not in [PurchaseRequestStatus.PENDING_APPROVAL, PurchaseRequestStatus.DRAFT]:
            raise ConflictException(
                f"Cannot reject request {req.request_number}. Current status is '{req.status.value}'."
            )

        now = datetime.now(timezone.utc)
        req.status = PurchaseRequestStatus.REJECTED

        # Record Approval Decision
        approval_record = ApprovalRecord(
            purchase_request_id=req.id,
            approver_id=approver.id,
            decision=ApprovalDecision.REJECTED,
            comments=comments,
            decision_timestamp=now,
        )
        db.add(approval_record)

        # Audit Log
        audit = AuditLog(
            actor_type=ActorType.USER,
            actor_id=str(approver.id),
            action="REJECT_PURCHASE_REQUEST",
            entity_type="PurchaseRequest",
            entity_id=str(req.id),
            payload_after={
                "request_number": req.request_number,
                "status": PurchaseRequestStatus.REJECTED.value,
                "approver_id": approver.id,
                "comments": comments,
            },
            description=f"Rejected purchase request {req.request_number}. Reason: {comments}",
        )
        db.add(audit)

        await db.commit()
        from app.services.purchase_request_service import PurchaseRequestService
        return await PurchaseRequestService.get_request_by_id(db, req.id)

    @staticmethod
    async def expire_stale_proposals(
        db: AsyncSession,
        max_age_hours: int = 24,
    ) -> int:
        """Finds and marks stale unapproved proposals as EXPIRED."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        query = select(PurchaseRequest).where(
            PurchaseRequest.status.in_([
                PurchaseRequestStatus.DRAFT,
                PurchaseRequestStatus.PENDING_APPROVAL,
            ]),
            PurchaseRequest.created_at < cutoff_time,
        )
        result = await db.execute(query)
        stale_requests = result.scalars().all()

        for req in stale_requests:
            req.status = PurchaseRequestStatus.EXPIRED
            audit = AuditLog(
                actor_type=ActorType.SYSTEM,
                actor_id="system_cron",
                action="EXPIRE_STALE_PURCHASE_REQUEST",
                entity_type="PurchaseRequest",
                entity_id=str(req.id),
                description=f"Purchase request {req.request_number} expired after {max_age_hours} hours without approval.",
            )
            db.add(audit)

        await db.commit()
        return len(stale_requests)
