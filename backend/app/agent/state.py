import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Structured state schema for the StockPilot AI LangGraph Workflow.
    Maintains conversation trajectory, extracted intents, retrieved inventory data,
    executed tool records, and workflow lifecycle status.
    """
    # Conversation Messages (Appended via LangGraph add_messages reducer)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Session Identifiers
    thread_id: str
    user_id: Optional[str]

    # Workflow Reasoning & Extracted Intent
    current_intent: Optional[str]  # e.g. LOW_STOCK_AUDIT, SUPPLIER_INQUIRY, DRAFT_PURCHASE_REQUEST
    retrieved_data: Dict[str, Any]
    proposed_actions: List[Dict[str, Any]]
    executed_tools: List[Dict[str, Any]]
    validation_errors: List[str]

    # Lifecycle & Loop Guard
    workflow_status: str  # IN_PROGRESS, COMPLETED, WAITING_INPUT, FAILED
    iteration_count: int
    final_response: Optional[str]
