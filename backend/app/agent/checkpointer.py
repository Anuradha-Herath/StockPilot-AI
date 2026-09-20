import asyncio
import logging
import sys
from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings

logger = logging.getLogger("stockpilot.checkpointer")

_global_memory_saver: Optional[MemorySaver] = None


def get_memory_checkpointer() -> MemorySaver:
    global _global_memory_saver
    if _global_memory_saver is None:
        _global_memory_saver = MemorySaver()
    return _global_memory_saver


async def get_postgres_checkpointer() -> BaseCheckpointSaver:
    """
    Returns an asynchronous PostgreSQL checkpointer using psycopg connection string.
    Automatically creates checkpoint tables if they don't already exist.
    Falls back gracefully to MemorySaver if unavailable or on incompatible event loops (e.g. Windows Proactor).
    """
    # Windows ProactorEventLoop is incompatible with psycopg async connection pool
    if sys.platform == "win32":
        try:
            loop = asyncio.get_running_loop()
            if "Proactor" in type(loop).__name__:
                return get_memory_checkpointer()
        except Exception:
            pass

    pool = None
    try:
        from psycopg_pool import AsyncConnectionPool
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Connection string for psycopg with quick connect timeout
        conn_str = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}?connect_timeout=2"
        pool = AsyncConnectionPool(conninfo=conn_str, max_size=10, open=False, timeout=2.0)
        await asyncio.wait_for(pool.open(), timeout=2.0)

        checkpointer = AsyncPostgresSaver(pool)
        await asyncio.wait_for(checkpointer.setup(), timeout=2.0)
        return checkpointer
    except Exception as e:
        logger.warning(f"Could not initialize Postgres checkpointer ({str(e)}). Falling back to MemorySaver.")
        if pool:
            try:
                await pool.close()
            except Exception:
                pass
        return get_memory_checkpointer()
