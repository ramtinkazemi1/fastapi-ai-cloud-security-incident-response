"""Database operations for security alerts."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, AuditEvent
from app.schemas.alert import AlertCreate, AlertSource, AlertStatus


class DuplicateAlertError(Exception):
    """Raised when a provider sends an alert already stored by the service."""


async def create_alert(
    session: AsyncSession,
    alert_data: AlertCreate,
    *,
    actor: str,
) -> Alert:
    """Persist an alert and translate its uniqueness conflict."""
    db_alert = Alert(**alert_data.model_dump())
    session.add(db_alert)

    try:
        await session.flush()
        session.add(
            AuditEvent(
                actor=actor,
                action="alert.created",
                resource_type="alert",
                resource_id=db_alert.id,
                details={
                    "source": db_alert.source,
                    "external_id": db_alert.external_id,
                },
            )
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DuplicateAlertError from exc

    await session.refresh(db_alert)
    return db_alert


async def get_alert(
    session: AsyncSession,
    alert_id: UUID,
) -> Alert | None:
    """Return an alert by primary key."""
    return await session.get(Alert, alert_id)


async def list_alerts(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    source: AlertSource | None = None,
    status: AlertStatus | None = None,
    minimum_severity: float | None = None,
) -> tuple[list[Alert], int]:
    """Return a filtered page and the total number of matching alerts."""
    filters = []
    if source is not None:
        filters.append(Alert.source == source.value)
    if status is not None:
        filters.append(Alert.status == status.value)
    if minimum_severity is not None:
        filters.append(Alert.severity >= minimum_severity)

    count_statement = select(func.count()).select_from(Alert).where(*filters)
    total = (await session.scalar(count_statement)) or 0

    statement = (
        select(Alert)
        .where(*filters)
        .order_by(Alert.occurred_at.desc(), Alert.id)
        .limit(limit)
        .offset(offset)
    )
    alerts = list((await session.scalars(statement)).all())
    return alerts, total


async def set_alert_status(
    session: AsyncSession,
    alert: Alert,
    status: AlertStatus,
    *,
    actor: str,
) -> Alert:
    """Move an alert to a new investigation state."""
    previous_status = alert.status
    alert.status = status.value
    session.add(
        AuditEvent(
            actor=actor,
            action="alert.status_changed",
            resource_type="alert",
            resource_id=alert.id,
            details={"from": previous_status, "to": status.value},
        )
    )
    await session.commit()
    await session.refresh(alert)
    return alert


async def save_analysis(
    session: AsyncSession,
    alert: Alert,
    *,
    summary: str,
    recommended_action: str,
    actor: str,
) -> Alert:
    """Persist AI triage output and its generation time."""
    alert.ai_summary = summary
    alert.recommended_action = recommended_action
    alert.analyzed_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor=actor,
            action="alert.analyzed",
            resource_type="alert",
            resource_id=alert.id,
            details={},
        )
    )
    await session.commit()
    await session.refresh(alert)
    return alert
