"""FastAPI dependency injection functions.

Centralized location for all API dependencies, including service instances,
authentication, and other shared resources.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from pymongo.mongo_client import MongoClient

from src.config import settings


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


def get_question_db_client(request: Request) -> MongoClient:
    """Get the Question DB MongoDB client from app state."""
    client = request.app.state.question_db_client
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question database not configured",
        )
    return client


def get_content_db_client(request: Request) -> MongoClient:
    """Get the Content DB MongoDB client from app state."""
    client = request.app.state.content_db_client
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content database not configured",
        )
    return client


# Type aliases for dependency injection
APIKeyDep = Annotated[None, Depends(verify_api_key)]
QuestionDBClient = Annotated[MongoClient, Depends(get_question_db_client)]
ContentDBClient = Annotated[MongoClient, Depends(get_content_db_client)]
