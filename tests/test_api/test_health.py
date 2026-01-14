"""Tests for health check endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint returns correct status.

    Args:
        client: FastAPI test client fixture
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "model_loaded" in data
    assert isinstance(data["model_loaded"], bool)


def test_readiness_check(client: TestClient) -> None:
    """Test the readiness check endpoint.

    Args:
        client: FastAPI test client fixture
    """
    response = client.get("/api/v1/ready")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["ready", "not_ready"]


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns API information.

    Args:
        client: FastAPI test client fixture
    """
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data
