from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertSource(StrEnum):
    """Supported security-alert producers."""

    GUARD_DUTY = "guardduty"
    WAZUH = "wazuh"


class AlertStatus(StrEnum):
    """Investigation state used by the incident-response workflow."""

    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertBase(BaseModel):
    """Fields shared by alert request and response contracts."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: AlertSource
    external_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=10_000)
    severity: float = Field(ge=0, le=10)
    occurred_at: datetime
    account_id: str | None = Field(
        default=None,
        pattern=r"^\d{12}$",
    )
    region: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
    )
    resource: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
    )


class AlertCreate(AlertBase):
    """Validated alert data accepted by the ingestion API."""

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject timestamps that do not identify a timezone."""

        # Pydantic converts the incoming timestamp string to a datetime before
        # this validator runs. A datetime is timezone-aware only when it has
        # both timezone metadata and a usable UTC offset.
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")

        # Field validators must return the value Pydantic should store.
        return value


class AlertRead(AlertBase):
    """A persisted alert returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID | None
    status: AlertStatus
    ai_summary: str | None
    recommended_action: str | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AlertStatusUpdate(BaseModel):
    """Allowed operator update for an alert investigation."""

    status: AlertStatus


class AlertList(BaseModel):
    """Paginated alert collection with navigation metadata."""

    items: list[AlertRead]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
