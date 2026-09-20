from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestCorrelationMiddleware, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    setup_logging()
    yield
    # Shutdown logic


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Autonomous Inventory & Procurement System with Human-in-the-Loop Safeguards",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add Request Correlation and Access Logging Middleware
    app.add_middleware(RequestCorrelationMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Include API routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Top-level root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "documentation": "/docs",
            "api_v1": settings.API_V1_PREFIX,
        }

    return app


app = create_application()
