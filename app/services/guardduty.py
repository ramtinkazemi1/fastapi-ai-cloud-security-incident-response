"""Normalize AWS GuardDuty findings into the internal alert contract."""

from typing import Any

from app.schemas.alert import AlertCreate, AlertSource
from app.schemas.guardduty import GuardDutyFinding


def _first_string(value: Any, *paths: tuple[str, ...]) -> str | None:
    """Return the first non-empty string found in nested provider data."""
    for path in paths:
        current = value
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                current = current[index] if index < len(current) else None
            else:
                current = None
                break
        if isinstance(current, str) and current:
            return current
    return None


def normalize_guardduty_finding(
    finding: GuardDutyFinding,
) -> AlertCreate:
    """Convert provider-specific names into a vendor-neutral alert."""
    resource = _first_string(
        finding.resource,
        ("instanceDetails", "instanceId"),
        ("accessKeyDetails", "userName"),
        ("s3BucketDetails", "0", "name"),
    )

    return AlertCreate(
        source=AlertSource.GUARD_DUTY,
        external_id=finding.id,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        occurred_at=finding.updated_at,
        account_id=finding.account_id,
        region=finding.region,
        resource=resource,
    )
