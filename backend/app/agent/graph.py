import json
import logging
from typing import Any, Dict, List, Literal, Optional
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_adapter import LLMAdapter
from app.agent.prompts import STOCKPILOT_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools.base import ToolResult
from app.agent.tools.inventory_tools import (
    calculate_reorder_recommendation,
    find_low_stock_products,
    get_inventory,
    get_supplier_options,
    search_products,
)
from app.agent.tools.procurement_tools import (
    create_draft_purchase_request,
    get_purchase_request_status,
)
from app.agent.tools.registry import TOOL_REGISTRY

logger = logging.getLogger("stockpilot.graph")

MAX_ITERATIONS = 8


def build_agent_tools(db: AsyncSession) -> Dict[str, StructuredTool]:
    """Constructs LangChain StructuredTools bound to the provided database session."""
    tools = {}

    # 1. search_products
    async def _search_products(**kwargs) -> str:
        schema = TOOL_REGISTRY["search_products"]["input_schema"]
        res: ToolResult = await search_products(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["search_products"] = StructuredTool.from_function(
        coroutine=_search_products,
        name="search_products",
        description=TOOL_REGISTRY["search_products"]["description"],
        args_schema=TOOL_REGISTRY["search_products"]["input_schema"],
    )

    # 2. get_inventory
    async def _get_inventory(**kwargs) -> str:
        schema = TOOL_REGISTRY["get_inventory"]["input_schema"]
        res: ToolResult = await get_inventory(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["get_inventory"] = StructuredTool.from_function(
        coroutine=_get_inventory,
        name="get_inventory",
        description=TOOL_REGISTRY["get_inventory"]["description"],
        args_schema=TOOL_REGISTRY["get_inventory"]["input_schema"],
    )

    # 3. find_low_stock_products
    async def _find_low_stock_products(**kwargs) -> str:
        schema = TOOL_REGISTRY["find_low_stock_products"]["input_schema"]
        res: ToolResult = await find_low_stock_products(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["find_low_stock_products"] = StructuredTool.from_function(
        coroutine=_find_low_stock_products,
        name="find_low_stock_products",
        description=TOOL_REGISTRY["find_low_stock_products"]["description"],
        args_schema=TOOL_REGISTRY["find_low_stock_products"]["input_schema"],
    )

    # 4. get_supplier_options
    async def _get_supplier_options(**kwargs) -> str:
        schema = TOOL_REGISTRY["get_supplier_options"]["input_schema"]
        res: ToolResult = await get_supplier_options(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["get_supplier_options"] = StructuredTool.from_function(
        coroutine=_get_supplier_options,
        name="get_supplier_options",
        description=TOOL_REGISTRY["get_supplier_options"]["description"],
        args_schema=TOOL_REGISTRY["get_supplier_options"]["input_schema"],
    )

    # 5. calculate_reorder_recommendation
    async def _calculate_reorder_recommendation(**kwargs) -> str:
        schema = TOOL_REGISTRY["calculate_reorder_recommendation"]["input_schema"]
        res: ToolResult = await calculate_reorder_recommendation(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["calculate_reorder_recommendation"] = StructuredTool.from_function(
        coroutine=_calculate_reorder_recommendation,
        name="calculate_reorder_recommendation",
        description=TOOL_REGISTRY["calculate_reorder_recommendation"]["description"],
        args_schema=TOOL_REGISTRY["calculate_reorder_recommendation"]["input_schema"],
    )

    # 6. create_draft_purchase_request
    async def _create_draft_purchase_request(**kwargs) -> str:
        schema = TOOL_REGISTRY["create_draft_purchase_request"]["input_schema"]
        res: ToolResult = await create_draft_purchase_request(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["create_draft_purchase_request"] = StructuredTool.from_function(
        coroutine=_create_draft_purchase_request,
        name="create_draft_purchase_request",
        description=TOOL_REGISTRY["create_draft_purchase_request"]["description"],
        args_schema=TOOL_REGISTRY["create_draft_purchase_request"]["input_schema"],
    )

    # 7. get_purchase_request_status
    async def _get_purchase_request_status(**kwargs) -> str:
        schema = TOOL_REGISTRY["get_purchase_request_status"]["input_schema"]
        res: ToolResult = await get_purchase_request_status(db=db, args=schema(**kwargs))
        return json.dumps(res.model_dump(mode="json"), default=str)

    tools["get_purchase_request_status"] = StructuredTool.from_function(
        coroutine=_get_purchase_request_status,
        name="get_purchase_request_status",
        description=TOOL_REGISTRY["get_purchase_request_status"]["description"],
        args_schema=TOOL_REGISTRY["get_purchase_request_status"]["input_schema"],
    )

    return tools


def create_stockpilot_workflow(db: AsyncSession, custom_llm: Optional[Any] = None) -> StateGraph:
    """
    Constructs the LangGraph StateGraph workflow for StockPilot AI.
    """
    tools_dict = build_agent_tools(db)
    tool_list = list(tools_dict.values())
    llm = custom_llm or LLMAdapter.get_chat_model()
    llm_with_tools = llm.bind_tools(tool_list)

    # ------------------------------------------------------------------
    # Node 1: Intent Analyzer
    # ------------------------------------------------------------------
    async def intent_analyzer_node(state: AgentState) -> Dict[str, Any]:
        last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
        msg_lower = str(last_user_msg).lower()

        intent = "GENERAL_CONVERSATION"
        if "low stock" in msg_lower or "running low" in msg_lower or "shortage" in msg_lower:
            intent = "LOW_STOCK_AUDIT"
        elif "draft" in msg_lower and ("purchase" in msg_lower or "request" in msg_lower or "order" in msg_lower):
            intent = "DRAFT_PURCHASE_REQUEST"
        elif "supplier" in msg_lower or "vendor" in msg_lower:
            intent = "SUPPLIER_INQUIRY"
        elif "status" in msg_lower and ("pr-" in msg_lower or "request" in msg_lower):
            intent = "STATUS_CHECK"
        elif "stock" in msg_lower or "inventory" in msg_lower or "how many" in msg_lower:
            intent = "INVENTORY_LOOKUP"

        return {
            "current_intent": intent,
            "workflow_status": "IN_PROGRESS",
            "validation_errors": [],
        }

    # ------------------------------------------------------------------
    # Node 2: Agent Reasoner (Calls LLM)
    # ------------------------------------------------------------------
    async def agent_reasoner_node(state: AgentState) -> Dict[str, Any]:
        system_msg = SystemMessage(content=STOCKPILOT_SYSTEM_PROMPT)
        convo_messages = [system_msg] + [m for m in state["messages"] if not isinstance(m, SystemMessage)]

        ai_response: AIMessage = await llm_with_tools.ainvoke(convo_messages)
        new_count = state.get("iteration_count", 0) + 1

        return {
            "messages": [ai_response],
            "iteration_count": new_count,
        }

    # ------------------------------------------------------------------
    # Node 3: Tool Validator (Safety Guard & Loop Prevention)
    # ------------------------------------------------------------------
    async def tool_validator_node(state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])
        validation_errors = list(state.get("validation_errors", []))
        executed_tools = list(state.get("executed_tools", []))

        executed_signatures = {
            f"{t.get('tool_name')}_{json.dumps(t.get('arguments', {}), sort_keys=True)}"
            for t in executed_tools
        }

        for tc in tool_calls:
            t_name = tc.get("name")
            t_args = tc.get("args", {})
            sig = f"{t_name}_{json.dumps(t_args, sort_keys=True)}"

            if t_name not in tools_dict:
                validation_errors.append(f"Unauthorized or unknown tool requested: '{t_name}'")
                executed_tools.append({
                    "tool_name": t_name,
                    "arguments": t_args,
                    "success": False,
                    "summary": f"Unauthorized or unregistered tool: {t_name}",
                })
            elif sig in executed_signatures:
                validation_errors.append(f"Repeated tool call detected for '{t_name}'. Aborting loop.")

        return {
            "validation_errors": validation_errors,
            "executed_tools": executed_tools,
        }

    # ------------------------------------------------------------------
    # Node 4: Tool Executor
    # ------------------------------------------------------------------
    async def tool_executor_node(state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])

        tool_messages: List[ToolMessage] = []
        executed_tools = list(state.get("executed_tools", []))
        retrieved_data = dict(state.get("retrieved_data", {}))

        for tc in tool_calls:
            t_name = tc.get("name")
            t_args = tc.get("args", {})
            t_id = tc.get("id", "call_1")

            tool_obj = tools_dict.get(t_name)
            if not tool_obj:
                continue

            try:
                res_str = await tool_obj.ainvoke(t_args)
                parsed = json.loads(res_str)

                retrieved_data[f"{t_name}_{t_id}"] = parsed.get("data")
                executed_tools.append({
                    "tool_name": t_name,
                    "arguments": t_args,
                    "success": parsed.get("success", False),
                    "summary": f"Executed {t_name}",
                    "data": parsed.get("data"),
                })
                tool_messages.append(ToolMessage(content=res_str, tool_call_id=t_id))
            except Exception as e:
                err_msg = json.dumps({"success": False, "error": str(e)})
                tool_messages.append(ToolMessage(content=err_msg, tool_call_id=t_id))
                executed_tools.append({
                    "tool_name": t_name,
                    "arguments": t_args,
                    "success": False,
                    "summary": f"Error: {str(e)}",
                })

        return {
            "messages": tool_messages,
            "executed_tools": executed_tools,
            "retrieved_data": retrieved_data,
        }

    # ------------------------------------------------------------------
    # Node 5: Response Formatter
    # ------------------------------------------------------------------
    async def response_formatter_node(state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        reply_content = last_msg.content if isinstance(last_msg, AIMessage) else ""

        if state.get("validation_errors"):
            errors_str = "; ".join(state["validation_errors"])
            reply_content += f"\n\n> ⚠️ **Note:** {errors_str}"

        return {
            "final_response": reply_content,
            "workflow_status": "COMPLETED",
        }

    # ------------------------------------------------------------------
    # Conditional Routing Edges
    # ------------------------------------------------------------------
    def should_continue_from_agent(state: AgentState) -> Literal["tool_validator", "response_formatter"]:
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])
        iteration = state.get("iteration_count", 0)

        if not tool_calls or iteration >= MAX_ITERATIONS:
            return "response_formatter"
        return "tool_validator"

    def should_continue_from_validator(state: AgentState) -> Literal["tool_executor", "response_formatter"]:
        errors = state.get("validation_errors", [])
        if any("Unauthorized" in err or "Aborting loop" in err for err in errors):
            return "response_formatter"
        return "tool_executor"

    # ------------------------------------------------------------------
    # Graph Construction
    # ------------------------------------------------------------------
    workflow = StateGraph(AgentState)

    workflow.add_node("intent_analyzer", intent_analyzer_node)
    workflow.add_node("agent_reasoner", agent_reasoner_node)
    workflow.add_node("tool_validator", tool_validator_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("response_formatter", response_formatter_node)

    workflow.set_entry_point("intent_analyzer")
    workflow.add_edge("intent_analyzer", "agent_reasoner")
    workflow.add_conditional_edges("agent_reasoner", should_continue_from_agent)
    workflow.add_conditional_edges("tool_validator", should_continue_from_validator)
    workflow.add_edge("tool_executor", "agent_reasoner")
    workflow.add_edge("response_formatter", END)

    return workflow
