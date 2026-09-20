from typing import List
from fastapi import APIRouter
from app.api.deps import DBSessionDep
from app.schemas.inventory import (
    InventoryLevelResponse,
    LowStockItemResponse,
    StockAdjustmentRequest,
    StockSummaryResponse,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/summary", response_model=StockSummaryResponse)
async def get_inventory_summary(db: DBSessionDep):
    """Retrieve high-level inventory metrics: healthy, low stock, out of stock, and total valuation."""
    return await InventoryService.get_stock_summary(db=db)


@router.get("/low-stock", response_model=List[LowStockItemResponse])
async def list_low_stock_items(db: DBSessionDep):
    """List all products below their reorder point with calculated shortages and supplier estimates."""
    return await InventoryService.get_low_stock_items(db=db)


@router.post("/{product_id}/adjust", response_model=InventoryLevelResponse)
async def adjust_stock(
    product_id: int,
    payload: StockAdjustmentRequest,
    db: DBSessionDep,
):
    """Adjust product stock quantity with audited tracking."""
    return await InventoryService.adjust_stock(
        db=db,
        product_id=product_id,
        payload=payload,
    )
