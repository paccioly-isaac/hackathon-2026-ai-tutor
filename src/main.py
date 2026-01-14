"""Main FastAPI application entry point.

This module initializes the FastAPI application, configures middleware,
and registers all route handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.api.routes import ai
from src.models.schemas import HealthResponse
from src.database.mongo_db_io import connect_to_mongo


class AITutorException(Exception):
    """Custom exception for AI Tutor errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown events."""
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Debug mode: {settings.debug}")

    # Initialize MongoDB clients
    app.state.question_db_client = None
    app.state.content_db_client = None

    if settings.question_db_uri:
        app.state.question_db_client = connect_to_mongo(settings.question_db_uri)
        print("Question DB client initialized")

    if settings.content_db_uri:
        app.state.content_db_client = connect_to_mongo(settings.content_db_uri)
        print("Content DB client initialized")

    yield

    # Cleanup MongoDB connections
    if app.state.question_db_client:
        app.state.question_db_client.close()
    if app.state.content_db_client:
        app.state.content_db_client.close()
    print("Shutting down application")


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered tutoring system API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AITutorException)
async def ai_tutor_exception_handler(
    request: Request, exc: AITutorException
) -> JSONResponse:
    """Handle custom AI tutor exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "details": {},
            "status_code": 500,
        },
    )


# Register routers
app.include_router(ai.router, prefix=settings.api_v1_prefix)


# Health check endpoints
@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        model_loaded=True,  # In production, check if models are actually loaded
    )


@app.get("/api/v1/health", tags=["health"], response_model=HealthResponse)
async def health_check_v1() -> HealthResponse:
    """Health check endpoint (API v1)."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        model_loaded=True,
    )


@app.get("/api/v1/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    # In production, check database connections, model loading, etc.
    return {"status": "ready"}


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint providing basic API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
