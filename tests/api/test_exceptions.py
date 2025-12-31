import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validation_exception_structure(client: AsyncClient):
    """
    Test that validation errors (RequestValidationError) return the standardized JSON structure.
    Target: POST /api/auth/login with empty body.
    """
    response = await client.post("/api/auth/login", json={})

    assert response.status_code == 422
    data = response.json()

    assert "status_code" in data
    assert data["status_code"] == 422
    assert "message" in data
    assert data["message"] == "Validation Error"
    assert "details" in data
    # Details should be a string representation of the pydantic errors
    assert isinstance(data["details"], str)


@pytest.mark.asyncio
async def test_not_found_exception_structure(client: AsyncClient):
    """
    Test that 404 errors (StarletteHTTPException) return the standardized JSON structure.
    Target: GET /non-existent-route
    """
    response = await client.get("/api/non-existent-route-should-fail")

    assert response.status_code == 404
    data = response.json()

    assert "status_code" in data
    assert data["status_code"] == 404
    assert "message" in data
    assert data["message"] == "Not Found"
    assert data["details"] is None
