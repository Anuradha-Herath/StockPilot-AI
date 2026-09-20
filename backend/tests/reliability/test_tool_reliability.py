import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import ToolResult, safe_tool_executor
from app.agent.tools.schemas import (
    GetInventoryInput,
    GetSupplierOptionsInput,
    SearchProductsInput,
)
from app.agent.tools.inventory_tools import get_inventory, search_products, get_supplier_options
from app.core.exceptions import NotFoundException, BadRequestException


class TestToolReliability:
    """
    Failure-injection and reliability test suite:
    - Verifies timeout enforcement via safe_tool_executor
    - Verifies bounded retries for safe read-only queries
    - Verifies zero-retry guarantee on mutating operations
    - Verifies structured error envelopes for validation and missing resources
    """

    @pytest.mark.asyncio
    async def test_tool_timeout_enforcement(self):
        """Simulate a tool that hangs longer than timeout limit."""
        @safe_tool_executor("slow_mock_tool", max_retries=0, timeout_seconds=0.1)
        async def slow_fn():
            await asyncio.sleep(0.5)
            return "finished"

        result: ToolResult = await slow_fn()
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "ToolTimeoutError"
        assert result.error.category == "TIMEOUT_ERROR"
        assert "exceeded time limit" in result.error.message

    @pytest.mark.asyncio
    async def test_safe_tool_retry_on_transient_db_error(self):
        """Simulate transient database failure that recovers on retry."""
        call_count = 0

        class OperationalError(Exception):
            pass

        @safe_tool_executor("flaky_read_tool", max_retries=2, retry_backoff=0.01, timeout_seconds=1.0)
        async def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("Connection lost to database")
            return {"status": "recovered"}

        result: ToolResult = await flaky_fn()
        assert result.success is True
        assert result.data == {"status": "recovered"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_mutating_tool_never_retries(self):
        """Verify mutating tools with max_retries=0 fail immediately on error without duplicate executions."""
        call_count = 0

        class DatabaseError(Exception):
            pass

        @safe_tool_executor("mutating_action", max_retries=0, timeout_seconds=1.0)
        async def mutating_fn():
            nonlocal call_count
            call_count += 1
            raise DatabaseError("DB deadlocked during insert")

        result: ToolResult = await mutating_fn()
        assert result.success is False
        assert call_count == 1
        assert result.error.retry_count == 0

    @pytest.mark.asyncio
    async def test_resource_not_found_envelope(self, db_session: AsyncSession):
        """Verify querying non-existent supplier options returns a structured error envelope."""
        args = GetSupplierOptionsInput(product_id=999999)
        result = await get_supplier_options(db=db_session, args=args)
        assert result.success is False
        assert result.error is not None
        assert result.error.category == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_search_products_bounded_output(self, db_session: AsyncSession):
        """Verify search tool handles extreme query lengths gracefully."""
        args = SearchProductsInput(query="NonExistentItemWithVeryLongName" * 5, limit=5)
        result = await search_products(db=db_session, args=args)
        assert result.success is True
        assert result.data.total_found == 0
        assert len(result.data.products) == 0
