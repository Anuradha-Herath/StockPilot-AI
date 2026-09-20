import logging
import uuid
from typing import Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.checkpointer import get_memory_checkpointer, get_postgres_checkpointer
from app.agent.graph import create_stockpilot_workflow
from app.agent.state import AgentState
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallLog

logger = logging.getLogger("stockpilot.agent")


class AgentService:
    @staticmethod
    async def process_chat(
        db: AsyncSession,
        request: ChatRequest,
        custom_llm: Optional[Any] = None,
        checkpointer_type: Optional[str] = None,
    ) -> ChatResponse:
        """
        Executes the LangGraph StateGraph workflow for the given user request.
        Maintains conversational state and execution checkpoints associated with thread_id.
        """
        thread_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"

        # Select checkpointer based on environment and overrides
        use_memory = (
            checkpointer_type == "memory"
            or custom_llm is not None
            or settings.ENVIRONMENT == "testing"
        )

        if use_memory:
            checkpointer = get_memory_checkpointer()
        else:
            checkpointer = await get_postgres_checkpointer()

        # Build and compile workflow
        workflow = create_stockpilot_workflow(db=db, custom_llm=custom_llm)
        app = workflow.compile(checkpointer=checkpointer)

        # Prepare initial messages from request history
        initial_messages = []
        for h in request.history:
            if h.role == "user":
                initial_messages.append(HumanMessage(content=h.content))
            elif h.role == "assistant":
                initial_messages.append(AIMessage(content=h.content))

        initial_messages.append(HumanMessage(content=request.message))

        initial_state: AgentState = {
            "messages": initial_messages,
            "thread_id": thread_id,
            "user_id": "current_operator",
            "current_intent": None,
            "retrieved_data": {},
            "proposed_actions": [],
            "executed_tools": [],
            "validation_errors": [],
            "workflow_status": "IN_PROGRESS",
            "iteration_count": 0,
            "final_response": None,
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Execute the graph
        final_state = await app.ainvoke(initial_state, config=config)

        tool_logs: List[ToolCallLog] = [
            ToolCallLog(
                tool_name=t.get("tool_name", "unknown"),
                arguments=t.get("arguments", {}),
                success=t.get("success", True),
                result_summary=t.get("summary", "Tool executed"),
                data=t.get("data"),
            )
            for t in final_state.get("executed_tools", [])
        ]

        reply = final_state.get("final_response") or "I processed your request, but did not generate a reply."

        return ChatResponse(
            reply=reply,
            tool_calls=tool_logs,
            session_id=thread_id,
        )
