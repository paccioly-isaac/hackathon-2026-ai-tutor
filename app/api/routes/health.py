"""Health check and status endpoints.

Provides endpoints for monitoring service health, readiness, and version info.
"""

from fastapi import APIRouter, status
from app.models.schemas import HealthResponse
from app.config import settings
from app.api.dependencies import AIServiceDep

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the service is running and healthy",
)
async def health_check(ai_service: AIServiceDep) -> HealthResponse:
    """Perform a health check on the service.

    Returns:
        HealthResponse with current service status
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        model_loaded=ai_service.is_model_loaded(),
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
)
async def readiness_check(ai_service: AIServiceDep) -> dict[str, str]:
    """Check if the service is ready to handle requests.

    Returns:
        Dictionary with readiness status
    """
    if not ai_service.is_model_loaded():
        return {"status": "not_ready", "reason": "AI model not loaded"}

    return {"status": "ready"}
