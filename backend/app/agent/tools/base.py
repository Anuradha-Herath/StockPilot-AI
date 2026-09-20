import functools
import traceback
from typing import Any, Callable, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolError(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ToolResult(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ToolError] = None

    @classmethod
    def ok(cls, data: T) -> "ToolResult[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str, details: Optional[dict[str, Any]] = None) -> "ToolResult[T]":
        return cls(
            success=False,
            data=None,
            error=ToolError(code=code, message=message, details=details),
        )


def safe_tool_executor(tool_name: str):
    """
    Decorator that wraps async tool execution:
    - Traps domain and validation exceptions into standard ToolResult.fail() payloads.
    - Prevents unhandled crashes from aborting the AI agent workflow.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> ToolResult:
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult.ok(result)
            except Exception as exc:
                error_code = exc.__class__.__name__
                error_msg = str(exc)
                details = getattr(exc, "details", {})
                return ToolResult.fail(
                    code=error_code,
                    message=f"[{tool_name}] {error_msg}",
                    details=details,
                )
        return wrapper
    return decorator
