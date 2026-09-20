import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch
from langchain_core.messages import AIMessage


@pytest.mark.asyncio
async def test_chat_api_endpoint(client: AsyncClient, seeded_db_session: AsyncSession):
    # Mock LLM response to ensure deterministic offline test
    mock_reply = AIMessage(content="I checked the inventory and Whole Milk Test has 5 units.")

    with patch("app.agent.llm_adapter.LLMAdapter.get_chat_model") as mock_get_llm:
        from tests.unit.test_agent_service import DeterministicMockChatModel
        mock_get_llm.return_value = DeterministicMockChatModel(responses=[mock_reply])

        payload = {
            "message": "Check the stock of milk",
            "history": [],
            "session_id": "test_session_1",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "Whole Milk Test" in data["reply"]
        assert data["session_id"] == "test_session_1"
