"""Background analysis-job response contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobStatus(StrEnum):
    """Observable states for a background analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJobRead(BaseModel):
    """Trackable status returned to the API client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID
    requested_by: str
    status: JobStatus
    error: str | None
    created_at: datetime
    updated_at: datetime
