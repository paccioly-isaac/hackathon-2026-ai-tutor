"""Custom exception classes for the application.

Defines domain-specific exceptions that can be raised throughout
the application for better error handling and reporting.
"""

from typing import Any, Optional


class AITutorException(Exception):
    """Base exception for all AI Tutor application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            status_code: HTTP status code for this error
            details: Additional context about the error
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ModelNotAvailableError(AITutorException):
    """Raised when the AI model is not available or fails to load."""

    def __init__(self, message: str = "AI model is not available") -> None:
        super().__init__(message=message, status_code=503)


class InvalidInputError(AITutorException):
    """Raised when user input validation fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class RateLimitExceededError(AITutorException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, status_code=429)
