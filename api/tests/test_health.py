import pytest
from httpx import ASGITransport, AsyncClient

from app import __version__
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test service root endpoint returns basic info."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "cortex-api"
        assert data["version"] == __version__
        assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_check_root():
    """Test /health endpoint returns operational status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "cortex-api"
        assert data["version"] == __version__


@pytest.mark.asyncio
async def test_health_check_v1():
    """Test /api/v1/health endpoint returns operational status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "cortex-api"
        assert data["version"] == __version__
