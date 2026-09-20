import json
import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_adapter import LLMAdapter
from app.agent.prompts import STOCKPILOT_SYSTEM_PROMPT
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
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ToolCallLog

logger = logging.getLogger("stockpilot.agent")


class AgentService:
    @staticmethod
    def _create_langchain_tools(db: AsyncSession) -> List[StructuredTool]:
        """Convert Phase 2 typed tools into LangChain StructuredTools bound to the active DB session."""
        tools = []

        # 1. search_products
        async def _search_products(**kwargs) -> str:
            schema = TOOL_REGISTRY["search_products"]["input_schema"]
            res: ToolResult = await search_products(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_search_products,
                name="search_products",
                description=TOOL_REGISTRY["search_products"]["description"],
                args_schema=TOOL_REGISTRY["search_products"]["input_schema"],
            )
        )

        # 2. get_inventory
        async def _get_inventory(**kwargs) -> str:
            schema = TOOL_REGISTRY["get_inventory"]["input_schema"]
            res: ToolResult = await get_inventory(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_get_inventory,
                name="get_inventory",
                description=TOOL_REGISTRY["get_inventory"]["description"],
                args_schema=TOOL_REGISTRY["get_inventory"]["input_schema"],
            )
        )

        # 3. find_low_stock_products
        async def _find_low_stock_products(**kwargs) -> str:
            schema = TOOL_REGISTRY["find_low_stock_products"]["input_schema"]
            res: ToolResult = await find_low_stock_products(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_find_low_stock_products,
                name="find_low_stock_products",
                description=TOOL_REGISTRY["find_low_stock_products"]["description"],
                args_schema=TOOL_REGISTRY["find_low_stock_products"]["input_schema"],
            )
        )

        # 4. get_supplier_options
        async def _get_supplier_options(**kwargs) -> str:
            schema = TOOL_REGISTRY["get_supplier_options"]["input_schema"]
            res: ToolResult = await get_supplier_options(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_get_supplier_options,
                name="get_supplier_options",
                description=TOOL_REGISTRY["get_supplier_options"]["description"],
                args_schema=TOOL_REGISTRY["get_supplier_options"]["input_schema"],
            )
        )

        # 5. calculate_reorder_recommendation
        async def _calculate_reorder_recommendation(**kwargs) -> str:
            schema = TOOL_REGISTRY["calculate_reorder_recommendation"]["input_schema"]
            res: ToolResult = await calculate_reorder_recommendation(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_calculate_reorder_recommendation,
                name="calculate_reorder_recommendation",
                description=TOOL_REGISTRY["calculate_reorder_recommendation"]["description"],
                args_schema=TOOL_REGISTRY["calculate_reorder_recommendation"]["input_schema"],
            )
        )

        # 6. create_draft_purchase_request
        async def _create_draft_purchase_request(**kwargs) -> str:
            schema = TOOL_REGISTRY["create_draft_purchase_request"]["input_schema"]
            res: ToolResult = await create_draft_purchase_request(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_create_draft_purchase_request,
                name="create_draft_purchase_request",
                description=TOOL_REGISTRY["create_draft_purchase_request"]["description"],
                args_schema=TOOL_REGISTRY["create_draft_purchase_request"]["input_schema"],
            )
        )

        # 7. get_purchase_request_status
        async def _get_purchase_request_status(**kwargs) -> str:
            schema = TOOL_REGISTRY["get_purchase_request_status"]["input_schema"]
            res: ToolResult = await get_purchase_request_status(db=db, args=schema(**kwargs))
            return json.dumps(res.model_dump(mode="json"), default=str)

        tools.append(
            StructuredTool.from_function(
                coroutine=_get_purchase_request_status,
                name="get_purchase_request_status",
                description=TOOL_REGISTRY["get_purchase_request_status"]["description"],
                args_schema=TOOL_REGISTRY["get_purchase_request_status"]["input_schema"],
            )
        )

        return tools

    @staticmethod
    async def process_chat(
        db: AsyncSession,
        request: ChatRequest,
        custom_llm: Optional[Any] = None,
        max_iterations: int = 10,
    ) -> ChatResponse:
        """
        Executes the cyclical Agent reasoning loop:
        1. Formulates message payload with SystemPrompt + History + User Message.
        2. Binds validated Phase 2 tools to the LLM.
        3. Executes tool calls iteratively until LLM returns final natural language response.
        """
        llm = custom_llm or LLMAdapter.get_chat_model()
        tools = AgentService._create_langchain_tools(db=db)
        tool_map = {t.name: t for t in tools}

        llm_with_tools = llm.bind_tools(tools)

        # Build message history
        messages: List[BaseMessage] = [SystemMessage(content=STOCKPILOT_SYSTEM_PROMPT)]
        for h in request.history:
            if h.role == "user":
                messages.append(HumanMessage(content=h.content))
            elif h.role == "assistant":
                messages.append(AIMessage(content=h.content))

        messages.append(HumanMessage(content=request.message))

        executed_tool_logs: List[ToolCallLog] = []

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            ai_message: AIMessage = await llm_with_tools.ainvoke(messages)
            messages.append(ai_message)

            # Check if LLM requested tool calls
            tool_calls = getattr(ai_message, "tool_calls", [])
            if not tool_calls:
                # LLM finished reasoning and produced final textual answer
                return ChatResponse(
                    reply=ai_message.content,
                    tool_calls=executed_tool_logs,
                    session_id=request.session_id,
                )

            # Execute tool calls
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool_args = tc.get("args", {})
                tool_call_id = tc.get("id", "call_1")

                logger.info(f"Agent calling tool '{tool_name}' with args: {tool_args}")

                if tool_name not in tool_map:
                    error_payload = json.dumps({"success": False, "error": f"Tool '{tool_name}' not found."})
                    messages.append(ToolMessage(content=error_payload, tool_call_id=tool_call_id))
                    executed_tool_logs.append(
                        ToolCallLog(
                            tool_name=tool_name,
                            arguments=tool_args,
                            success=False,
                            result_summary="Tool not registered in system.",
                        )
                    )
                    continue

                tool_obj = tool_map[tool_name]
                try:
                    tool_output_str = await tool_obj.ainvoke(tool_args)
                    parsed_res = json.loads(tool_output_str)
                    is_success = parsed_res.get("success", False)

                    executed_tool_logs.append(
                        ToolCallLog(
                            tool_name=tool_name,
                            arguments=tool_args,
                            success=is_success,
                            result_summary=f"Executed {tool_name} successfully." if is_success else "Tool returned error.",
                        )
                    )
                    messages.append(ToolMessage(content=tool_output_str, tool_call_id=tool_call_id))
                except Exception as ex:
                    logger.error(f"Error executing tool '{tool_name}': {str(ex)}")
                    error_payload = json.dumps({"success": False, "error": str(ex)})
                    messages.append(ToolMessage(content=error_payload, tool_call_id=tool_call_id))
                    executed_tool_logs.append(
                        ToolCallLog(
                            tool_name=tool_name,
                            arguments=tool_args,
                            success=False,
                            result_summary=f"Exception: {str(ex)}",
                        )
                    )

        # Fallback if iterations exceed limit
        return ChatResponse(
            reply="I analyzed the available inventory data, but could not complete the final response within the iteration limit.",
            tool_calls=executed_tool_logs,
            session_id=request.session_id,
        )
