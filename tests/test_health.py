"""Tests for operational health endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_healthy() -> None:
    """The health endpoint reports that the API process is available."""

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_request_counters() -> None:
    """Prometheus can scrape the application's HTTP metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/metrics/")

    assert response.status_code == 200
    assert "cir_http_requests_total" in response.text
