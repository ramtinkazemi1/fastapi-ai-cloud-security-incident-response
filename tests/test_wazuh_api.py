"""Tests for Wazuh alert normalization."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_wazuh_ingestion_normalizes_rule_and_agent(
    client: AsyncClient,
) -> None:
    """A Wazuh payload becomes a vendor-neutral alert."""
    response = await client.post(
        "/api/v1/alerts/ingest/wazuh",
        json={
            "id": "wazuh-event-1",
            "timestamp": "2026-08-08T19:00:00Z",
            "rule": {
                "id": "5710",
                "level": 12,
                "description": "Multiple authentication failures",
            },
            "agent": {"id": "001", "name": "web-server-1"},
            "data": {"srcip": "203.0.113.10"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "wazuh"
    assert body["severity"] == 8
    assert body["resource"] == "web-server-1"
    assert "203.0.113.10" in body["description"]
