from fastapi import APIRouter
from app.api.v1.endpoints import (
    approvals,
    audit_logs,
    chat,
    health,
    inventory,
    products,
    purchase_orders,
    purchase_requests,
    suppliers,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(inventory.router)
api_router.include_router(suppliers.router)
api_router.include_router(purchase_requests.router)
api_router.include_router(approvals.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(audit_logs.router)
api_router.include_router(chat.router)
