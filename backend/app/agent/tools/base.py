import asyncio
import functools
import logging
from typing import Any, Callable, Generic, Optional, TypeVar
from pydantic import BaseModel

logger = logging.getLogger("stockpilot.tools")

T = TypeVar("T")


class ToolError(BaseModel):
    code: str
    message: str
    category: str = "GENERAL_ERROR"  # VALIDATION_ERROR, TIMEOUT_ERROR, DATABASE_ERROR, RESOURCE_NOT_FOUND, GENERAL_ERROR
    retry_count: int = 0
    details: Optional[dict[str, Any]] = None


class ToolResult(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ToolError] = None

    @classmethod
    def ok(cls, data: T) -> "ToolResult[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        category: str = "GENERAL_ERROR",
        retry_count: int = 0,
        details: Optional[dict[str, Any]] = None,
    ) -> "ToolResult[T]":
        return cls(
            success=False,
            data=None,
            error=ToolError(
                code=code,
                message=message,
                category=category,
                retry_count=retry_count,
                details=details,
            ),
        )


def safe_tool_executor(
    tool_name: str,
    max_retries: int = 0,
    retry_backoff: float = 0.2,
    timeout_seconds: float = 10.0,
):
    """
    Decorator that wraps async tool execution:
    - Enforces execution timeouts (preventing hung DB connections or external delays).
    - Traps domain and validation exceptions into standard ToolResult.fail() envelopes.
    - Performs bounded exponential backoff retries ONLY for designated safe/read-only tools.
    - Strictly avoids retrying non-idempotent mutations (max_retries=0 by default).
    - Categorizes error codes for clear AI agent recovery reasoning.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> ToolResult:
            retries = 0
            while True:
                try:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds,
                    )
                    if isinstance(result, ToolResult):
                        return result
                    return ToolResult.ok(result)
                except asyncio.TimeoutError:
                    if retries < max_retries:
                        retries += 1
                        delay = retry_backoff * (2 ** (retries - 1))
                        logger.warning(
                            f"[{tool_name}] Timed out after {timeout_seconds}s. Retry {retries}/{max_retries} in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    return ToolResult.fail(
                        code="ToolTimeoutError",
                        message=f"[{tool_name}] Operation exceeded time limit of {timeout_seconds}s.",
                        category="TIMEOUT_ERROR",
                        retry_count=retries,
                        details={"timeout_seconds": timeout_seconds},
                    )
                except Exception as exc:
                    error_code = exc.__class__.__name__
                    error_msg = str(exc)
                    details = getattr(exc, "details", {})

                    category = "GENERAL_ERROR"
                    if "NotFound" in error_code:
                        category = "RESOURCE_NOT_FOUND"
                    elif "Validation" in error_code or "BadRequest" in error_code or "ValueError" in error_code:
                        category = "VALIDATION_ERROR"
                    elif "OperationalError" in error_code or "Database" in error_code:
                        category = "DATABASE_ERROR"

                    # Only retry on transient database or operational failures for safe tools
                    if category == "DATABASE_ERROR" and retries < max_retries:
                        retries += 1
                        delay = retry_backoff * (2 ** (retries - 1))
                        logger.warning(
                            f"[{tool_name}] Database error: {error_msg}. Retry {retries}/{max_retries} in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    return ToolResult.fail(
                        code=error_code,
                        message=f"[{tool_name}] {error_msg}",
                        category=category,
                        retry_count=retries,
                        details=details,
                    )
        return wrapper
    return decorator
