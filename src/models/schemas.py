"""Pydantic models for request/response validation.

All API request and response models are defined here using Pydantic
for automatic validation, serialization, and documentation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Health check endpoint response."""

    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Whether AI model is loaded")


class TutorRequest(BaseModel):
    """Request model for AI tutor interactions."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Student's question or prompt",
    )
    context: Optional[str] = Field(
        None,
        max_length=5000,
        description="Additional context for the question",
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Model temperature (0.0-2.0)",
    )
    session_id: str = Field(
        ...,
        description="Session ID for conversation tracking",
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        """Validate that question is not just whitespace."""
        if not v.strip():
            raise ValueError("Question cannot be empty or whitespace only")
        return v.strip()


class TutorResponse(BaseModel):
    """Response model for AI tutor interactions."""

    answer: str = Field(..., description="AI-generated response")
    model_used: str = Field(..., description="Name of the model used")
    tokens_used: Optional[int] = Field(None, description="Number of tokens consumed")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[dict] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")
