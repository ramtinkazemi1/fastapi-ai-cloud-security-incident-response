"""Tests for alert endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_validate_alert_accepts_valid_payload() -> None:
    """A valid JSON request is validated and returned by the API."""

    # This dictionary is the HTTP request body, not AsyncClient configuration.
    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test description",
        "severity": 7.5,
        "occurred_at": "2026-07-20T12:00:00Z",
    }

    # ASGITransport connects HTTPX directly to FastAPI without a real server.
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/alerts/validate",
            json=payload,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "guardduty"
    assert body["severity"] == 7.5
    assert isinstance(body["occurred_at"], str)


@pytest.mark.asyncio
async def test_validate_alert_rejects_invalid_severity() -> None:
    """Invalid severity values are rejected before route execution."""

    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test description",
        "severity": 12,
        "occurred_at": "2026-07-20T12:00:00Z",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/alerts/validate",
            json=payload,
        )

    assert response.status_code == 422

    body = response.json()
    error = body["detail"][0]

    assert error["loc"] == ["body", "severity"]
    assert error["type"] == "less_than_equal"
