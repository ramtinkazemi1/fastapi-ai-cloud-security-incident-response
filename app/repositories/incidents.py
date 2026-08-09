"""Database operations for incidents and their audit trail."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, AuditEvent, Incident
from app.schemas.incident import IncidentCreate, IncidentStatus


class AlertLinkError(Exception):
    """Raised when requested alerts cannot be linked to an incident."""


async def create_incident(
    session: AsyncSession,
    data: IncidentCreate,
    *,
    actor: str,
) -> Incident:
    """Create an incident, link its alerts, and record one audit event."""
    alert_ids = list(dict.fromkeys(data.alert_ids))
    alerts = list(
        (
            await session.scalars(
                select(Alert).where(Alert.id.in_(alert_ids)),
            )
        ).all()
    )
    if len(alerts) != len(alert_ids):
        raise AlertLinkError("One or more alerts were not found")
    if any(alert.incident_id is not None for alert in alerts):
        raise AlertLinkError("One or more alerts already belong to an incident")

    incident = Incident(
        title=data.title,
        summary=data.summary,
        severity=data.severity,
        created_by=actor,
    )
    session.add(incident)
    await session.flush()

    for alert in alerts:
        alert.incident_id = incident.id

    session.add(
        AuditEvent(
            actor=actor,
            action="incident.created",
            resource_type="incident",
            resource_id=incident.id,
            details={"alert_ids": [str(alert_id) for alert_id in alert_ids]},
        )
    )
    await session.commit()
    await session.refresh(incident)
    return incident


async def get_incident(
    session: AsyncSession,
    incident_id: UUID,
) -> Incident | None:
    """Return an incident by primary key."""
    return await session.get(Incident, incident_id)


async def get_incident_alert_ids(
    session: AsyncSession,
    incident_id: UUID,
) -> list[UUID]:
    """Return IDs of alerts linked to one incident."""
    return list(
        (
            await session.scalars(
                select(Alert.id)
                .where(Alert.incident_id == incident_id)
                .order_by(Alert.occurred_at),
            )
        ).all()
    )


async def list_incidents(
    session: AsyncSession,
) -> list[Incident]:
    """Return incidents newest first."""
    return list(
        (
            await session.scalars(
                select(Incident).order_by(Incident.created_at.desc()),
            )
        ).all()
    )


async def set_incident_status(
    session: AsyncSession,
    incident: Incident,
    new_status: IncidentStatus,
    *,
    actor: str,
) -> Incident:
    """Update an incident and append its status transition audit event."""
    previous_status = incident.status
    incident.status = new_status.value
    session.add(
        AuditEvent(
            actor=actor,
            action="incident.status_changed",
            resource_type="incident",
            resource_id=incident.id,
            details={
                "from": previous_status,
                "to": new_status.value,
            },
        )
    )
    await session.commit()
    await session.refresh(incident)
    return incident


async def list_audit_events(
    session: AsyncSession,
    *,
    limit: int,
) -> list[AuditEvent]:
    """Return the latest append-only audit records."""
    return list(
        (
            await session.scalars(
                select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit),
            )
        ).all()
    )
