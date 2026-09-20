import contextvars
import json
import logging
import re
import time
import uuid
from typing import Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold the current request ID across async tasks
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

# Sensitive keys to redact in log records and dictionaries
SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "groq_api_key",
    "authorization",
    "cookie",
    "credit_card",
}

# Regex to match sensitive key-value pairs in unstructured text strings
SENSITIVE_PATTERN = re.compile(
    r'(?i)(api[_-]?key|password|secret|bearer|authorization|token)["\']?\s*[:=]\s*["\']?([^"\'\s,;]+)["\']?'
)


def redact_sensitive_text(text: str) -> str:
    """Redacts sensitive credentials and tokens in raw strings."""
    if not isinstance(text, str):
        return text
    return SENSITIVE_PATTERN.sub(r'\1="[REDACTED]"', text)


def redact_sensitive_dict(data: Any) -> Any:
    """Recursively redacts sensitive keys in nested dicts/lists."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                cleaned[k] = redact_sensitive_dict(v)
            elif isinstance(v, str):
                cleaned[k] = redact_sensitive_text(v)
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]
    elif isinstance(data, str):
        return redact_sensitive_text(data)
    return data


class StructuredLogFormatter(logging.Formatter):
    """
    JSON / Structured log formatter that injects correlation request_id
    and automatically sanitizes sensitive fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get() or getattr(record, "request_id", "none")
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "request_id": req_id,
            "message": redact_sensitive_text(record.getMessage()),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["details"] = redact_sensitive_dict(record.extra_data)

        return json.dumps(log_entry)


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware that assigns a unique Correlation Request ID to every request,
    attaches it to the response headers, and logs duration metrics.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate Request ID
        incoming_req_id = request.headers.get("X-Request-ID")
        req_id = incoming_req_id if incoming_req_id else str(uuid.uuid4())
        
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        logger = logging.getLogger("stockpilot.access")
        logger.info(
            f"Incoming {request.method} {request.url.path}",
            extra={"request_id": req_id},
        )

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            logger.info(
                f"Completed {request.method} {request.url.path} with status {response.status_code} in {duration_ms:.2f}ms",
                extra={"request_id": req_id},
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Unhandled exception during {request.method} {request.url.path} after {duration_ms:.2f}ms: {exc}",
                exc_info=True,
                extra={"request_id": req_id},
            )
            raise
        finally:
            request_id_ctx.reset(token)


def setup_logging(level: str = "INFO") -> None:
    """Configures structured logging handlers across the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if already configured
    if not any(isinstance(h.formatter, StructuredLogFormatter) for h in root_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        root_logger.addHandler(handler)
