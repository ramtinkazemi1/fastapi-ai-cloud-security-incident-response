"""Tests for GuardDuty field aliases and schema boundaries."""

from datetime import datetime
from app.schemas.guardduty import GuardDutyFinding


def test_aws_aliases() -> None:
    """AWS camelCase fields round-trip through Python field aliases."""

    payload = {
        "id": "finding-123",
        "type": "UnauthorizedAccess:EC2/SSHBruteForce",
        "title": "EC2 instance received SSH brute-force traffic",
        "description": "A remote host made repeated SSH connection attempts.",
        "severity": 7.2,
        "accountId": "123456789012",
        "region": "us-west-2",
        "updatedAt": "2026-07-20T12:00:00Z",
        "service": {"additional": "provider data"},
    }

    finding = GuardDutyFinding.model_validate(payload)

    assert isinstance(finding.updated_at, datetime)
    assert not hasattr(finding, "service")

    serialized = finding.model_dump(mode="json", by_alias=True)

    assert serialized["accountId"] == "123456789012"
    assert "account_id" not in serialized
    assert isinstance(serialized["updatedAt"], str)
    assert "service" not in serialized
