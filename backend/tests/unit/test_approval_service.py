from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ConflictException, NotFoundException
from app.db.models import (
    AuditLog,
    Product,
    PurchaseOrder,
    PurchaseOrderStatus,
    PurchaseRequest,
    PurchaseRequestStatus,
    Supplier,
    SupplierProduct,
    User,
    UserRole,
)
from app.schemas.approval import ApprovalDecisionRequest
from app.schemas.purchase_request import PurchaseRequestItemBase
from app.services.approval_service import ApprovalService
from app.services.purchase_request_service import PurchaseRequestService


@pytest.mark.asyncio
async def test_compute_proposal_hash():
    """Hash should be deterministic regardless of item insertion order."""
    supplier_id = 1
    items_order_1 = [(101, 50, Decimal("2.50")), (102, 20, Decimal("4.00"))]
    items_order_2 = [(102, 20, Decimal("4.00")), (101, 50, Decimal("2.50"))]

    hash_1 = ApprovalService.compute_proposal_hash(supplier_id, items_order_1)
    hash_2 = ApprovalService.compute_proposal_hash(supplier_id, items_order_2)

    assert hash_1 == hash_2
    assert len(hash_1) == 64  # SHA-256 hex length


@pytest.mark.asyncio
async def test_submit_for_approval_success(seeded_db_session: AsyncSession):
    """Submits a DRAFT proposal and verifies status transition and audit logging."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    requester = (
        await seeded_db_session.execute(
            select(User).where(User.role == UserRole.OPERATOR)
        )
    ).scalars().first()

    # Create draft request
    draft_req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=15, estimated_unit_cost=Decimal("3.00"))],
        reason="Weekly inventory replenishment",
    )
    assert draft_req.status == PurchaseRequestStatus.DRAFT

    # Submit for approval
    submitted_req = await ApprovalService.submit_for_approval(
        db=seeded_db_session,
        request_id=draft_req.id,
        requester=requester,
    )

    assert submitted_req.status == PurchaseRequestStatus.PENDING_APPROVAL
    assert submitted_req.requester_id == requester.id

    # Verify audit log
    audit = (
        await seeded_db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "SUBMIT_FOR_APPROVAL",
                AuditLog.entity_id == str(submitted_req.id),
            )
        )
    ).scalars().first()
    assert audit is not None
    assert audit.actor_id == str(requester.id)


@pytest.mark.asyncio
async def test_submit_for_approval_invalid_status(seeded_db_session: AsyncSession):
    """Submitting a proposal that is not in DRAFT status should raise ConflictException."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()

    draft_req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=15, estimated_unit_cost=Decimal("3.00"))],
    )
    db_req = await seeded_db_session.get(PurchaseRequest, draft_req.id)
    db_req.status = PurchaseRequestStatus.APPROVED
    await seeded_db_session.commit()

    with pytest.raises(ConflictException):
        await ApprovalService.submit_for_approval(
            db=seeded_db_session,
            request_id=draft_req.id,
        )


@pytest.mark.asyncio
async def test_get_pending_approvals(seeded_db_session: AsyncSession):
    """Verifies listing of pending approvals with calculated hash and items."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    requester = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    draft_req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=20, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(
        db=seeded_db_session,
        request_id=draft_req.id,
        requester=requester,
    )

    pending = await ApprovalService.get_pending_approvals(db=seeded_db_session)
    assert len(pending) >= 1
    target = next((p for p in pending if p.request_id == draft_req.id), None)
    assert target is not None
    assert target.supplier_name == supplier.name
    assert target.requester_name == requester.full_name
    assert len(target.proposal_version_hash) == 64


@pytest.mark.asyncio
async def test_approve_and_create_order_success(seeded_db_session: AsyncSession):
    """Tests the complete end-to-end authorized approval & PO execution flow."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    # 1. Create and submit PR by operator
    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=25, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    # 2. Get pending approvals to obtain proposal hash
    pending_list = await ApprovalService.get_pending_approvals(db=seeded_db_session)
    pending_summary = next(p for p in pending_list if p.request_id == req.id)
    proposal_hash = pending_summary.proposal_version_hash

    # 3. Manager approves proposal
    decision = ApprovalDecisionRequest(
        proposal_version_hash=proposal_hash,
        comments="Approved for urgent weekend restocking.",
        idempotency_key="idemp-key-test-100",
    )
    result = await ApprovalService.approve_and_create_order(
        db=seeded_db_session,
        request_id=req.id,
        approver=manager,
        payload=decision,
    )

    assert result.purchase_order_id is not None
    assert result.order_number.startswith("PO-")
    assert result.status == PurchaseOrderStatus.ISSUED.value
    assert result.approved_by_id == manager.id
    assert result.total_amount == Decimal("75.00")
    assert "TX-" in result.transmission_id

    # 4. Verify DB records
    po = (
        await seeded_db_session.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == result.purchase_order_id)
        )
    ).scalar_one()
    assert po.approved_by_id == manager.id
    assert po.status == PurchaseOrderStatus.ISSUED


@pytest.mark.asyncio
async def test_approve_unauthorized_role(seeded_db_session: AsyncSession):
    """An OPERATOR role cannot approve purchase proposals."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id)

    decision = ApprovalDecisionRequest(
        proposal_version_hash="dummy_hash",
        comments="Trying to self approve as operator",
    )

    with pytest.raises(AppException) as exc_info:
        await ApprovalService.approve_and_create_order(
            db=seeded_db_session,
            request_id=req.id,
            approver=operator,
            payload=decision,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_approve_self_approval_prohibited(seeded_db_session: AsyncSession):
    """A Manager who requested the proposal cannot approve their own proposal."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()

    # Manager requests proposal
    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=manager)

    pending_list = await ApprovalService.get_pending_approvals(db=seeded_db_session)
    summary = next(p for p in pending_list if p.request_id == req.id)

    decision = ApprovalDecisionRequest(
        proposal_version_hash=summary.proposal_version_hash,
        comments="Attempting self-approval",
    )

    with pytest.raises(AppException) as exc_info:
        await ApprovalService.approve_and_create_order(
            db=seeded_db_session,
            request_id=req.id,
            approver=manager,  # Same user
            payload=decision,
        )
    assert exc_info.value.status_code == 403
    assert "prohibited from approving their own" in exc_info.value.message


@pytest.mark.asyncio
async def test_approve_modified_proposal_hash_mismatch(seeded_db_session: AsyncSession):
    """If the supplier prices change or the hash does not match, approval is blocked."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    # Supply an invalid/stale hash
    decision = ApprovalDecisionRequest(
        proposal_version_hash="0000000000000000000000000000000000000000000000000000000000000000",
        comments="Approving with stale client state",
    )

    with pytest.raises(ConflictException) as exc_info:
        await ApprovalService.approve_and_create_order(
            db=seeded_db_session,
            request_id=req.id,
            approver=manager,
            payload=decision,
        )
    assert "Proposal verification failed" in exc_info.value.message


@pytest.mark.asyncio
async def test_approve_idempotency(seeded_db_session: AsyncSession):
    """Submitting the same idempotency key prevents duplicate execution."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    operator = (await seeded_db_session.execute(select(User).where(User.role == UserRole.OPERATOR))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id, requester=operator)

    pending_list = await ApprovalService.get_pending_approvals(db=seeded_db_session)
    summary = next(p for p in pending_list if p.request_id == req.id)

    idemp_key = "idemp-key-unique-777"
    decision = ApprovalDecisionRequest(
        proposal_version_hash=summary.proposal_version_hash,
        comments="First execution",
        idempotency_key=idemp_key,
    )

    # First call succeeds
    await ApprovalService.approve_and_create_order(
        db=seeded_db_session,
        request_id=req.id,
        approver=manager,
        payload=decision,
    )

    # Second call with same idempotency key fails with ConflictException
    with pytest.raises(ConflictException) as exc_info:
        await ApprovalService.approve_and_create_order(
            db=seeded_db_session,
            request_id=req.id,
            approver=manager,
            payload=decision,
        )
    assert "Duplicate execution prevented" in exc_info.value.message


@pytest.mark.asyncio
async def test_reject_request_success(seeded_db_session: AsyncSession):
    """Rejecting a request transitions it to REJECTED and creates no PO."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()
    manager = (await seeded_db_session.execute(select(User).where(User.role == UserRole.MANAGER))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )
    await ApprovalService.submit_for_approval(db=seeded_db_session, request_id=req.id)

    rejected_req = await ApprovalService.reject_request(
        db=seeded_db_session,
        request_id=req.id,
        approver=manager,
        comments="Over budget for this category for Q3.",
    )

    assert rejected_req.status == PurchaseRequestStatus.REJECTED

    # Ensure no PO was created
    po_count = (await seeded_db_session.execute(select(PurchaseOrder))).scalars().all()
    assert len(po_count) == 0


@pytest.mark.asyncio
async def test_expire_stale_proposals(seeded_db_session: AsyncSession):
    """Proposals older than threshold hours are marked EXPIRED."""
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    product = (await seeded_db_session.execute(select(Product))).scalars().first()

    req = await PurchaseRequestService.create_draft_request(
        db=seeded_db_session,
        supplier_id=supplier.id,
        items=[PurchaseRequestItemBase(product_id=product.id, quantity=10, estimated_unit_cost=Decimal("3.00"))],
    )

    # Manually backdate created_at to 48 hours ago on ORM entity
    db_req = await seeded_db_session.get(PurchaseRequest, req.id)
    db_req.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
    await seeded_db_session.commit()

    expired_count = await ApprovalService.expire_stale_proposals(
        db=seeded_db_session,
        max_age_hours=24,
    )

    assert expired_count >= 1
    await seeded_db_session.refresh(db_req)
    assert db_req.status == PurchaseRequestStatus.EXPIRED
