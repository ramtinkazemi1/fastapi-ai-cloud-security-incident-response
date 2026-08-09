"""Incident workflow and audit response contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentStatus(StrEnum):
    """Simple incident lifecycle used by analysts."""

    OPEN = "open"
    CONTAINED = "contained"
    CLOSED = "closed"


class IncidentCreate(BaseModel):
    """Data required to group alerts into an incident."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=3, max_length=10_000)
    severity: float = Field(ge=0, le=10)
    alert_ids: list[UUID] = Field(min_length=1, max_length=100)


class IncidentRead(BaseModel):
    """Persisted incident with the IDs of its linked alerts."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    severity: float
    status: IncidentStatus
    created_by: str
    alert_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class IncidentStatusUpdate(BaseModel):
    """Allowed incident lifecycle update."""

    status: IncidentStatus


class AuditEventRead(BaseModel):
    """Append-only audit record safe for administrator review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: str
    action: str
    resource_type: str
    resource_id: UUID
    details: dict[str, Any]
    created_at: datetime
