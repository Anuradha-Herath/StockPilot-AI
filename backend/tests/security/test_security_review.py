import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.logging import redact_sensitive_dict, redact_sensitive_text
from app.db.models.user import User, UserRole
from app.db.models.purchase_request import PurchaseRequest, PurchaseRequestStatus, PriorityLevel
from app.db.models.supplier import Supplier
from app.services.approval_service import ApprovalService


class TestSecurityReview:
    """
    Security and Authorization Test Suite:
    - Role-Based Access Control (RBAC) validation
    - Self-approval and separation of duties checks
    - Cryptographic proposal snapshot integrity (SHA-256)
    - Sensitive credential redaction in logs and dictionaries
    - Correlation ID tracing headers
    """

    def test_log_sanitization_redacts_credentials(self):
        """Ensure sensitive tokens and passwords are scrubbed from text and dictionaries."""
        raw_text = 'User login failed with api_key="gsk_1234567890abcdef" and password="SecretPassword123!"'
        cleaned = redact_sensitive_text(raw_text)
        assert "gsk_1234567890abcdef" not in cleaned
        assert "SecretPassword123!" not in cleaned

        raw_dict = {
            "user_id": "usr_01",
            "api_key": "sk-real-secret-key-12345",
            "groq_api_key": "gsk_secret",
            "payload": {
                "password": "my_db_password",
                "normal_field": "fresh_produce",
            },
        }
        cleaned_dict = redact_sensitive_dict(raw_dict)
        assert cleaned_dict["api_key"] == "[REDACTED]"
        assert cleaned_dict["groq_api_key"] == "[REDACTED]"
        assert cleaned_dict["payload"]["password"] == "[REDACTED]"
        assert cleaned_dict["payload"]["normal_field"] == "fresh_produce"

    @pytest.mark.asyncio
    async def test_correlation_request_id_header(self, client: AsyncClient):
        """Verify API responses include X-Request-ID and X-Response-Time headers."""
        response = await client.get("/")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

    @pytest.mark.asyncio
    async def test_operator_cannot_approve_request(self, client: AsyncClient, db_session: AsyncSession):
        """Ensure OPERATOR role is forbidden from performing approval actions."""
        # Create a pending PR
        supplier = Supplier(
            name="Security Test Supplier",
            code="SEC-SUP-01",
            email="sec@supplier.com",
            is_active=True,
        )
        db_session.add(supplier)
        await db_session.commit()
        await db_session.refresh(supplier)

        pr = PurchaseRequest(
            request_number="PR-SEC-001",
            supplier_id=supplier.id,
            status=PurchaseRequestStatus.PENDING_APPROVAL,
            priority=PriorityLevel.MEDIUM,
            requester_id=None,
        )
        db_session.add(pr)
        await db_session.commit()
        await db_session.refresh(pr)

        # Create Operator User
        import uuid
        uid = uuid.uuid4().hex[:6]
        operator_user = User(
            email=f"operator_{uid}@stockpilot.local",
            username=f"test_operator_{uid}",
            full_name="Store Operator",
            hashed_password="hashed_pw_test",
            role=UserRole.OPERATOR,
            is_active=True,
        )
        db_session.add(operator_user)
        await db_session.commit()
        await db_session.refresh(operator_user)

        # Attempt to approve as OPERATOR
        response = await client.post(
            f"/api/v1/approvals/requests/{pr.id}/approve",
            json={"decision": "APPROVE", "proposal_version_hash": "dummy_hash", "comments": "Operator trying to approve"},
            headers={"X-User-Id": str(operator_user.id)},
        )
        # Should be forbidden 403
        assert response.status_code == 403
        data = response.json()
        error_msg = data.get("error", {}).get("message", "") or data.get("message", "")
        assert "MANAGER" in error_msg or "Manager" in error_msg or "denied" in error_msg.lower() or "forbidden" in error_msg.lower() or "insufficient" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_sha256_proposal_integrity_hash(self):
        """Verify SHA-256 hash generation is deterministic and detects any payload changes."""
        from decimal import Decimal
        items_1 = [(1, 100, Decimal("2.50"))]
        items_2 = [(1, 100, Decimal("2.50"))]
        items_tampered = [(1, 100, Decimal("2.51"))]

        hash_1 = ApprovalService.compute_proposal_hash(supplier_id=1, items=items_1)
        hash_2 = ApprovalService.compute_proposal_hash(supplier_id=1, items=items_2)
        hash_tampered = ApprovalService.compute_proposal_hash(supplier_id=1, items=items_tampered)

        assert hash_1 == hash_2
        assert hash_1 != hash_tampered
        assert len(hash_1) == 64  # Standard SHA-256 hex string length

