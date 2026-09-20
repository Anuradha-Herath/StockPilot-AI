import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit_log import ActorType, AuditLog


@pytest.mark.asyncio
async def test_list_audit_logs_api(client: AsyncClient, db_session: AsyncSession):
    # Add a sample audit log
    log = AuditLog(
        actor_type=ActorType.USER,
        actor_id="test_user_1",
        action="TEST_ACTION",
        entity_type="Product",
        entity_id="101",
        description="Test audit log entry for API verification",
    )
    db_session.add(log)
    await db_session.commit()

    response = await client.get("/api/v1/audit-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["action"] == "TEST_ACTION" for item in data["items"])
