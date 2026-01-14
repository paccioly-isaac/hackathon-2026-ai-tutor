"""AI tutor endpoints for student interactions.

Provides endpoints for students to ask questions and receive AI-powered
educational responses.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import TutorRequest, TutorResponse, ErrorResponse
from app.api.dependencies import AIServiceDep, APIKeyDep
from app.core.exceptions import AITutorException

router = APIRouter(prefix="/tutor", tags=["ai-tutor"])


@router.post(
    "/ask",
    response_model=TutorResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI tutor a question",
    description="Submit a question to the AI tutor and receive an educational response",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def ask_tutor(
    request: TutorRequest,
    ai_service: AIServiceDep,
    _: APIKeyDep,
) -> TutorResponse:
    """Process a student question and return an AI-generated response.

    Args:
        request: The tutor request with question and optional context
        ai_service: Injected AI service instance
        _: API key verification dependency

    Returns:
        TutorResponse with the AI-generated answer

    Raises:
        HTTPException: For various error conditions (validation, availability, etc.)
    """
    try:
        response = ai_service.generate_response(request)
        return response

    except AITutorException as e:
        # Domain-specific exceptions with predefined status codes
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "details": e.details},
        ) from e

    except Exception as e:
        # Unexpected errors - log and return generic message
        # In production, add proper logging here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "details": {}},
        ) from e


@router.get(
    "/models",
    status_code=status.HTTP_200_OK,
    summary="List available AI models",
    description="Get information about available AI models and their capabilities",
)
async def list_models(_: APIKeyDep) -> dict[str, list[dict[str, str]]]:
    """List available AI models.

    Args:
        _: API key verification dependency

    Returns:
        Dictionary containing list of available models
    """
    # Placeholder - in production, return actual available models
    return {
        "models": [
            {
                "id": "default-model",
                "name": "Default Educational Model",
                "description": "General-purpose educational AI model",
            }
        ]
    }
