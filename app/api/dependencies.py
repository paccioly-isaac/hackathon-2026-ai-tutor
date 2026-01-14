"""FastAPI dependency injection functions.

Centralized location for all API dependencies, including service instances,
authentication, and other shared resources.
"""

from typing import Annotated
from fastapi import Depends, Header, HTTPException, status
from app.services.ai_service import AIService, get_ai_service
from app.config import settings


def get_ai_service_dependency() -> AIService:
    """Dependency for injecting AI service into route handlers.

    Returns:
        AIService instance

    Raises:
        HTTPException: If service initialization fails
    """
    try:
        return get_ai_service(model_name=settings.model_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}",
        ) from e


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify API key if authentication is enabled.

    Args:
        x_api_key: API key from request header

    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Skip authentication if no API key is configured
    if settings.api_key is None:
        return

    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# Type aliases for dependency injection
AIServiceDep = Annotated[AIService, Depends(get_ai_service_dependency)]
APIKeyDep = Annotated[None, Depends(verify_api_key)]
