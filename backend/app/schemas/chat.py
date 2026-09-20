from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Text content of the message")


class ToolCallLog(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    result_summary: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question or procurement instruction")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")
    session_id: Optional[str] = Field(None, description="Optional session tracking ID")


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[ToolCallLog] = []
    session_id: Optional[str] = None
