"""Pytest configuration and shared fixtures.

This module provides common fixtures used across all test modules.
"""

from typing import Generator
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application.

    Yields:
        TestClient instance for making test requests
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_api_key() -> str:
    """Provide a mock API key for testing.

    Returns:
        Mock API key string
    """
    return "test-api-key-12345"
