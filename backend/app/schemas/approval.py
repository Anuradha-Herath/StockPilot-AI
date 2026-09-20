from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.approval import ApprovalDecision
from app.db.models.purchase_request import PriorityLevel, PurchaseRequestStatus
from app.schemas.purchase_request import PurchaseRequestItemResponse


class ApprovalDecisionRequest(BaseModel):
    proposal_version_hash: str = Field(
        ...,
        description="SHA-256 integrity hash of the proposal reviewed by manager",
    )
    comments: Optional[str] = Field(None, max_length=1000, description="Optional manager approval notes")
    idempotency_key: Optional[str] = Field(
        None,
        description="Client-supplied UUID to prevent duplicate PO creation on network retry",
    )


class ApprovalRejectionRequest(BaseModel):
    comments: str = Field(
        ..., min_length=3, max_length=1000, description="Mandatory rejection reason"
    )


class ApprovalRecordResponse(BaseModel):
    id: int
    purchase_request_id: Optional[int]
    purchase_order_id: Optional[int]
    approver_id: int
    approver_name: Optional[str] = None
    approver_email: Optional[str] = None
    decision: ApprovalDecision
    comments: Optional[str] = None
    decision_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PendingApprovalSummary(BaseModel):
    request_id: int
    request_number: str
    supplier_id: int
    supplier_name: str
    requester_id: Optional[int] = None
    requester_name: Optional[str] = None
    status: PurchaseRequestStatus
    priority: PriorityLevel
    reason: Optional[str] = None
    total_estimated_cost: Decimal
    proposal_version_hash: str
    items_count: int
    items: List[PurchaseRequestItemResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderExecutionResult(BaseModel):
    purchase_order_id: int
    order_number: str
    purchase_request_id: int
    request_number: str
    supplier_id: int
    supplier_name: str
    total_amount: Decimal
    currency: str
    status: str
    approved_by_id: int
    approved_by_name: str
    transmission_id: str
    created_at: datetime
