"""Tests for the external AI-provider boundary."""

from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.db.models import Alert
from app.services.ai import AIServiceError, OpenAIAlertAnalyzer


def sample_alert() -> Alert:
    """Build an unsaved alert suitable for provider-request tests."""
    return Alert(
        source="guardduty",
        external_id="finding-ai-test",
        title="Suspicious API activity",
        description="An unusual API call was detected.",
        severity=8.5,
        occurred_at=datetime.now(UTC),
        region="us-west-2",
    )


@pytest.mark.asyncio
async def test_analyzer_validates_structured_provider_output() -> None:
    """A valid provider response becomes typed triage guidance."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"summary":"High-risk API behavior.",'
                                '"recommended_action":"Disable the key."}'
                            )
                        }
                    }
                ]
            },
        )

    analyzer = OpenAIAlertAnalyzer(
        Settings(openai_api_key="test-key"),
        transport=httpx.MockTransport(handler),
    )

    result = await analyzer.analyze(sample_alert())

    assert result.summary == "High-risk API behavior."
    assert result.recommended_action == "Disable the key."


@pytest.mark.asyncio
async def test_analyzer_rejects_invalid_provider_output() -> None:
    """Malformed provider content cannot enter the alert record."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not JSON"}}]},
        )

    analyzer = OpenAIAlertAnalyzer(
        Settings(openai_api_key="test-key"),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(AIServiceError, match="invalid JSON"):
        await analyzer.analyze(sample_alert())
