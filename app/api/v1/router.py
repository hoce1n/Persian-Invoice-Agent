from fastapi import APIRouter

from app.api.v1 import invoice_endpoints

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(
    invoice_endpoints.router,
    tags=["invoices"],
)
