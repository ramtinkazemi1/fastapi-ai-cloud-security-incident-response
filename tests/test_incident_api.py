"""Tests for incident grouping and audit history."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_incident_workflow_records_audit_events(
    admin_client: AsyncClient,
) -> None:
    """An analyst can group an alert and transition the incident."""
    alert = (
        await admin_client.post(
            "/api/v1/alerts",
            json={
                "source": "guardduty",
                "external_id": "incident-alert-1",
                "title": "Suspicious cloud activity",
                "description": "An unusual API call was detected.",
                "severity": 8,
                "occurred_at": "2026-08-08T19:00:00Z",
            },
        )
    ).json()

    created = await admin_client.post(
        "/api/v1/incidents",
        json={
            "title": "Possible credential compromise",
            "summary": "Investigate the suspicious cloud API activity.",
            "severity": 8,
            "alert_ids": [alert["id"]],
        },
    )

    assert created.status_code == 201
    incident = created.json()
    assert incident["status"] == "open"
    assert incident["alert_ids"] == [alert["id"]]

    updated = await admin_client.patch(
        f"/api/v1/incidents/{incident['id']}/status",
        json={"status": "contained"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "contained"

    audit = await admin_client.get("/api/v1/audit-events")
    actions = {event["action"] for event in audit.json()}
    assert "incident.created" in actions
    assert "incident.status_changed" in actions
