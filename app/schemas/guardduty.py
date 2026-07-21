"""Pydantic contracts for AWS GuardDuty findings."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GuardDutyFinding(BaseModel):
    """Supported subset of an AWS GuardDuty finding."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    id: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=3, max_length=255)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=10_000)
    severity: float = Field(ge=0, le=10)
    account_id: str = Field(
        alias="accountId",
        pattern=r"^\d{12}$",
    )
    region: str = Field(min_length=3, max_length=32)
    updated_at: datetime = Field(alias="updatedAt")
