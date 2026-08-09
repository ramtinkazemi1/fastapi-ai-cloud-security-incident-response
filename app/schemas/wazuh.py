"""Supported subset of a Wazuh alert payload."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WazuhRule(BaseModel):
    """Wazuh rule metadata used for normalization."""

    model_config = ConfigDict(extra="ignore")

    id: str
    level: int = Field(ge=0, le=15)
    description: str = Field(min_length=3, max_length=200)


class WazuhAgent(BaseModel):
    """Agent identity associated with a Wazuh event."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = Field(min_length=1, max_length=255)


class WazuhAlert(BaseModel):
    """Provider payload accepted by the Wazuh ingestion endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=255)
    timestamp: datetime
    rule: WazuhRule
    agent: WazuhAgent
    data: dict[str, Any] = Field(default_factory=dict)
