from fastapi import APIRouter
from app.agent.agent_service import AgentService
from app.api.deps import DBSessionDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Agent Chat"])


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    payload: ChatRequest,
    db: DBSessionDep,
):
    """
    Conversational AI copilot endpoint.
    Processes user inventory and procurement requests via dynamic tool calling.
    """
    return await AgentService.process_chat(db=db, request=payload)
