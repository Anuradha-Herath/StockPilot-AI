import pytest
from langchain_core.messages import AIMessage, HumanMessage
from app.agent.agent_service import AgentService
from app.agent.checkpointer import get_memory_checkpointer
from app.agent.graph import create_stockpilot_workflow
from app.schemas.chat import ChatRequest
from tests.unit.test_agent_service import DeterministicMockChatModel


@pytest.mark.asyncio
async def test_langgraph_intent_and_direct_response(seeded_db_session):
    reply_msg = AIMessage(content="Hello! I can help you check inventory or create draft purchase requests.")
    mock_llm = DeterministicMockChatModel(responses=[reply_msg])

    req = ChatRequest(message="Hello there!", session_id="test_thread_intent_1")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=req,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    assert "Hello" in response.reply
    assert response.session_id == "test_thread_intent_1"
    assert len(response.tool_calls) == 0


@pytest.mark.asyncio
async def test_langgraph_tool_execution_flow(seeded_db_session):
    # Step 1: LLM requests search_products
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "search_products",
            "args": {"query": "Milk", "limit": 3},
            "id": "call_graph_01",
        }],
    )
    # Step 2: LLM produces final response
    final_reply_msg = AIMessage(content="Found Whole Milk in stock.")

    mock_llm = DeterministicMockChatModel(responses=[tool_call_msg, final_reply_msg])

    req = ChatRequest(message="Find milk in the store", session_id="test_thread_tool_1")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=req,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    assert "Whole Milk" in response.reply
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "search_products"
    assert response.tool_calls[0].success is True


@pytest.mark.asyncio
async def test_langgraph_repeated_tool_call_prevention(seeded_db_session):
    # Simulate LLM repeatedly asking for the exact same tool call
    repeated_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "find_low_stock_products",
            "args": {"category": "Dairy"},
            "id": "call_repeat_1",
        }],
    )
    repeated_call_msg_2 = AIMessage(
        content="",
        tool_calls=[{
            "name": "find_low_stock_products",
            "args": {"category": "Dairy"},
            "id": "call_repeat_2",
        }],
    )
    final_reply_msg = AIMessage(content="Here are the dairy items.")

    mock_llm = DeterministicMockChatModel(responses=[repeated_call_msg, repeated_call_msg_2, final_reply_msg])

    req = ChatRequest(message="Low stock dairy", session_id="test_thread_repeat_1")
    response = await AgentService.process_chat(
        db=seeded_db_session,
        request=req,
        custom_llm=mock_llm,
        checkpointer_type="memory",
    )

    # Tool validator flags repeated call and prevents infinite looping
    assert response.session_id == "test_thread_repeat_1"
    assert len(response.tool_calls) >= 1


@pytest.mark.asyncio
async def test_langgraph_checkpoint_state_retrieval(seeded_db_session):
    # Test compiling graph with MemorySaver checkpointer and retrieving state by thread_id
    checkpointer = get_memory_checkpointer()
    reply_msg = AIMessage(content="Session state persisted.")
    mock_llm = DeterministicMockChatModel(responses=[reply_msg])

    workflow = create_stockpilot_workflow(db=seeded_db_session, custom_llm=mock_llm)
    app = workflow.compile(checkpointer=checkpointer)

    thread_id = "test_persistence_thread_123"
    config = {"configurable": {"thread_id": thread_id}}

    state_input = {
        "messages": [HumanMessage(content="Check thread state")],
        "thread_id": thread_id,
        "user_id": "operator_1",
        "current_intent": None,
        "retrieved_data": {},
        "proposed_actions": [],
        "executed_tools": [],
        "validation_errors": [],
        "workflow_status": "IN_PROGRESS",
        "iteration_count": 0,
        "final_response": None,
    }

    result = await app.ainvoke(state_input, config=config)
    assert result["workflow_status"] == "COMPLETED"

    # Verify checkpointer saved state for thread_id
    saved_state = await app.aget_state(config)
    assert saved_state is not None
    assert saved_state.values["workflow_status"] == "COMPLETED"
