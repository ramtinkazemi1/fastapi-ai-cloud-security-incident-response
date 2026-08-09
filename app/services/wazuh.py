"""Normalize Wazuh alerts into the internal alert contract."""

from app.schemas.alert import AlertCreate, AlertSource
from app.schemas.wazuh import WazuhAlert


def normalize_wazuh_alert(alert: WazuhAlert) -> AlertCreate:
    """Map Wazuh's 0–15 rule level onto normalized 0–10 severity."""
    source_ip = alert.data.get("srcip")
    context = f"Detected by Wazuh agent {alert.agent.name}."
    if isinstance(source_ip, str) and source_ip:
        context += f" Source IP: {source_ip}."

    return AlertCreate(
        source=AlertSource.WAZUH,
        external_id=alert.id,
        title=alert.rule.description,
        description=context,
        severity=round(alert.rule.level * (10 / 15), 1),
        occurred_at=alert.timestamp,
        resource=alert.agent.name,
    )
