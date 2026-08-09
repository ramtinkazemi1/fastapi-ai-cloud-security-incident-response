"""Tests for alert endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.services.ai import OpenAIAlertAnalyzer, TriageResult


def alert_payload(
    external_id: str = "finding-123",
    severity: float = 7.5,
) -> dict[str, object]:
    """Build a valid normalized alert request."""
    return {
        "source": "guardduty",
        "external_id": external_id,
        "title": "Suspicious API activity",
        "description": "An unusual API call was detected.",
        "severity": severity,
        "occurred_at": "2026-07-20T12:00:00Z",
        "account_id": "123456789012",
        "region": "us-west-2",
    }


@pytest.mark.asyncio
async def test_create_and_retrieve_alert(client: AsyncClient) -> None:
    """A valid alert is persisted and available by UUID."""
    create_response = await client.post(
        "/api/v1/alerts",
        json=alert_payload(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "new"
    assert created["created_at"]

    get_response = await client.get(
        f"/api/v1/alerts/{created['id']}",
    )

    assert get_response.status_code == 200
    assert get_response.json()["external_id"] == "finding-123"


@pytest.mark.asyncio
async def test_duplicate_provider_alert_returns_conflict(
    client: AsyncClient,
) -> None:
    """Provider retries do not create duplicate normalized alerts."""
    first_response = await client.post(
        "/api/v1/alerts",
        json=alert_payload(),
    )
    duplicate_response = await client.post(
        "/api/v1/alerts",
        json=alert_payload(),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


@pytest.mark.asyncio
async def test_list_filters_and_paginates_alerts(
    client: AsyncClient,
) -> None:
    """List filters return matching rows and pagination metadata."""
    await client.post(
        "/api/v1/alerts",
        json=alert_payload("low", severity=2),
    )
    await client.post(
        "/api/v1/alerts",
        json=alert_payload("high", severity=9),
    )

    response = await client.get(
        "/api/v1/alerts",
        params={"minimum_severity": 5, "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["items"][0]["external_id"] == "high"


@pytest.mark.asyncio
async def test_status_update_supports_investigation_workflow(
    admin_client: AsyncClient,
) -> None:
    """Operators can move an alert into investigation."""
    created = (
        await admin_client.post(
            "/api/v1/alerts",
            json=alert_payload(),
        )
    ).json()

    response = await admin_client.patch(
        f"/api/v1/alerts/{created['id']}/status",
        json={"status": "investigating"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "investigating"


@pytest.mark.asyncio
async def test_unknown_alert_returns_not_found(client: AsyncClient) -> None:
    """A valid but unknown UUID receives a clear 404 response."""
    response = await client.get(f"/api/v1/alerts/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_severity_is_rejected(client: AsyncClient) -> None:
    """Invalid severity values are rejected before route execution."""
    response = await client.post(
        "/api/v1/alerts/validate",
        json=alert_payload(severity=12),
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "less_than_equal"


@pytest.mark.asyncio
async def test_missing_api_key_is_rejected(client: AsyncClient) -> None:
    """Protected alert routes require the configured API key."""
    client.headers.pop("X-API-Key")

    response = await client.get("/api/v1/alerts")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ai_analysis_is_persisted(
    admin_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validated provider output is stored on the analyzed alert."""

    async def fake_analyze(
        self: OpenAIAlertAnalyzer,
        alert: object,
    ) -> TriageResult:
        return TriageResult(
            summary="Likely compromised cloud credentials.",
            recommended_action="Disable the key and review CloudTrail.",
        )

    monkeypatch.setattr(OpenAIAlertAnalyzer, "analyze", fake_analyze)
    created = (
        await admin_client.post(
            "/api/v1/alerts",
            json=alert_payload(),
        )
    ).json()

    response = await admin_client.post(
        f"/api/v1/alerts/{created['id']}/analyze",
    )

    assert response.status_code == 202
    job = await admin_client.get(
        f"/api/v1/alerts/analysis-jobs/{response.json()['id']}",
    )
    assert job.json()["status"] == "completed"

    stored = await admin_client.get(f"/api/v1/alerts/{created['id']}")
    assert stored.json()["ai_summary"].startswith("Likely compromised")
