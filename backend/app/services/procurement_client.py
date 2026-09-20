import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from pydantic import BaseModel

logger = logging.getLogger("stockpilot.procurement_client")


class TransmissionReceipt(BaseModel):
    transmission_id: str
    supplier_id: int
    supplier_code: str
    order_number: str
    total_amount: Decimal
    status: str
    transmitted_at: datetime
    mock_mode: bool = True


class MockProcurementClient:
    """
    Mock supplier integration adapter.
    Simulates transmitting an approved Purchase Order payload to vendor endpoints
    via EDI or webhook without placing real contractual orders during development.
    """

    @staticmethod
    async def dispatch_purchase_order(
        supplier_id: int,
        supplier_code: str,
        order_number: str,
        total_amount: Decimal,
        items: list[Dict[str, Any]],
    ) -> TransmissionReceipt:
        transmission_id = f"EDI-TX-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc)

        logger.info(
            f"[MOCK PROCUREMENT] Dispatched PO '{order_number}' (Total: ${total_amount}) "
            f"to Supplier '{supplier_code}' (ID: {supplier_id}). Transmission ID: {transmission_id}"
        )

        return TransmissionReceipt(
            transmission_id=transmission_id,
            supplier_id=supplier_id,
            supplier_code=supplier_code,
            order_number=order_number,
            total_amount=total_amount,
            status="TRANSMISSION_CONFIRMED",
            transmitted_at=now,
            mock_mode=True,
        )
