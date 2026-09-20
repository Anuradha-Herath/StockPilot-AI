from typing import Any, List
import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.agent.agent_service import AgentService
from app.schemas.chat import ChatRequest


class DeterministicMockChatModel(BaseChatModel):
    responses: List[AIMessage] = Field(default_factory=list)
    call_count: int = 0

    def _generate(self, messages: List[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
        else:
            resp = AIMessage(content="Default mock response.")
        return ChatResult(generations=[ChatGeneration(message=resp)])

    @property
    def _llm_type(self) -> str:
        return "deterministic_mock"

    def bind_tools(self, tools: Any, **kwargs: Any):
        return self


@pytest.mark.asyncio
async def test_agent_tool_calling_loop_success(seeded_db_session):
    # Step 1: LLM returns a tool call to search_products
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "search_products",
            "args": {"query": "Milk", "limit": 2},
            "id": "call_123",
        }],
    )
    # Step 2: After receiving tool output, LLM outputs final answer
    final_reply_msg = AIMessage(content="We have Whole Milk Test in stock with 5 units available.")

    mock_llm = DeterministicMockChatModel(responses=[tool_call_msg, final_reply_msg])

    request = ChatRequest(message="What is the stock of milk?")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=request,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    assert "Whole Milk Test in stock" in response.reply
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "search_products"
    assert response.tool_calls[0].success is True


@pytest.mark.asyncio
async def test_agent_invalid_tool_name_handling(seeded_db_session):
    # LLM tries to call a nonexistent tool
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "execute_arbitrary_code",
            "args": {"code": "rm -rf /"},
            "id": "call_bad",
        }],
    )
    final_reply_msg = AIMessage(content="I cannot execute arbitrary operations.")

    mock_llm = DeterministicMockChatModel(responses=[tool_call_msg, final_reply_msg])

    request = ChatRequest(message="Run this script.")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=request,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].success is False
    assert "Unauthorized" in response.tool_calls[0].result_summary


@pytest.mark.asyncio
async def test_agent_direct_response_without_tools(seeded_db_session):
    final_reply_msg = AIMessage(content="Hello! I am StockPilot AI. How can I assist with inventory today?")
    mock_llm = DeterministicMockChatModel(responses=[final_reply_msg])

    request = ChatRequest(message="Hello!")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=request,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    assert response.reply == "Hello! I am StockPilot AI. How can I assist with inventory today?"
    assert len(response.tool_calls) == 0
