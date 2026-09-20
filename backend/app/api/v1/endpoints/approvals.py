from typing import List
from fastapi import APIRouter, Query, status
from app.api.deps import CurrentUserDep, DBSessionDep, ManagerUserDep
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalRejectionRequest,
    OrderExecutionResult,
    PendingApprovalSummary,
)
from app.schemas.purchase_request import PurchaseRequestResponse
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["Human Approvals & Execution"])


@router.post(
    "/requests/{request_id}/submit",
    response_model=PurchaseRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_request_for_approval(
    request_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    """
    Submits a DRAFT purchase request for manager approval.
    Transitions status to PENDING_APPROVAL and assigns the requester identity.
    """
    return await ApprovalService.submit_for_approval(
        db=db,
        request_id=request_id,
        requester=current_user,
    )


@router.get(
    "/pending",
    response_model=List[PendingApprovalSummary],
    status_code=status.HTTP_200_OK,
)
async def get_pending_approvals(
    db: DBSessionDep,
    manager: ManagerUserDep,
):
    """
    Lists all purchase requests currently pending manager approval.
    Includes deterministic proposal SHA-256 version hashes for UI verification.
    """
    return await ApprovalService.get_pending_approvals(db=db)


@router.post(
    "/requests/{request_id}/approve",
    response_model=OrderExecutionResult,
    status_code=status.HTTP_200_OK,
)
async def approve_purchase_request(
    request_id: int,
    payload: ApprovalDecisionRequest,
    db: DBSessionDep,
    manager: ManagerUserDep,
):
    """
    Approves a pending purchase request and executes purchase order issuance.
    - Strictly enforces Manager/Admin role.
    - Prohibits self-approval (requesters cannot approve their own requests).
    - Verifies proposal SHA-256 version integrity hash.
    - Enforces idempotency via optional idempotency_key.
    - Atomically creates PurchaseOrder and items in database.
    - Dispatches order via MockProcurementClient.
    - Writes immutable audit trail entry.
    """
    return await ApprovalService.approve_and_create_order(
        db=db,
        request_id=request_id,
        approver=manager,
        payload=payload,
    )


@router.post(
    "/requests/{request_id}/reject",
    response_model=PurchaseRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_purchase_request(
    request_id: int,
    payload: ApprovalRejectionRequest,
    db: DBSessionDep,
    manager: ManagerUserDep,
):
    """
    Rejects a purchase request with mandatory rejection reason comments.
    Does NOT issue any purchase order or mutate inventory.
    """
    return await ApprovalService.reject_request(
        db=db,
        request_id=request_id,
        approver=manager,
        comments=payload.comments,
    )


@router.post(
    "/expire-stale",
    status_code=status.HTTP_200_OK,
)
async def expire_stale_requests(
    db: DBSessionDep,
    manager: ManagerUserDep,
    max_age_hours: int = Query(24, ge=1, le=720, description="Proposal age threshold in hours"),
):
    """
    Finds and marks stale unapproved proposals as EXPIRED.
    """
    expired_count = await ApprovalService.expire_stale_proposals(
        db=db,
        max_age_hours=max_age_hours,
    )
    return {
        "success": True,
        "message": f"Successfully marked {expired_count} stale proposal(s) as EXPIRED.",
        "expired_count": expired_count,
        "threshold_hours": max_age_hours,
    }
