"""Tests for normalized security-alert validation."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.alert import AlertCreate, AlertSource


def test_valid_alert_deserializes_and_serializes() -> None:
    """A valid external payload converts safely in both directions."""

    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test Description",
        "severity": 7.5,
        "occurred_at": "2026-07-20T12:00:00Z",
    }

    alert = AlertCreate.model_validate(payload)

    assert AlertSource.GUARD_DUTY == alert.source
    assert isinstance(alert.occurred_at, datetime)
    assert alert.severity == 7.5

    serialized = alert.model_dump(mode="json")

    assert serialized["source"] == "guardduty"
    assert isinstance(serialized["occurred_at"], str)


def test_alert_rejects_out_of_range_severity() -> None:
    """Severity values above the normalized maximum are rejected."""

    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test Description",
        "severity": 12.5,
        "occurred_at": "2026-07-20T12:00:00Z",
    }

    with pytest.raises(ValidationError):
        AlertCreate.model_validate(payload)


def test_alert_rejects_timestamp_without_timezone() -> None:
    """Timezone-less timestamps are rejected."""

    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test Description",
        "severity": 7,
        "occurred_at": "2026-07-20T12:00:00",
    }

    with pytest.raises(ValidationError):
        AlertCreate.model_validate(payload)


def test_alert_rejects_unknown_field() -> None:
    """Fields outside the declared schema are rejected."""

    payload = {
        "source": "guardduty",
        "external_id": "finding-123",
        "title": "A title for testing",
        "description": "A test Description",
        "severity": 7.5,
        "occurred_at": "2026-07-20T12:00:00Z",
        "is_admin": True,
    }

    with pytest.raises(ValidationError):
        AlertCreate.model_validate(payload)
