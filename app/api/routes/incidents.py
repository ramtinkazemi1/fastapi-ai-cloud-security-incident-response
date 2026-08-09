"""Analyst incident workflow and administrator audit routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, require_roles
from app.db.models import Incident
from app.db.session import get_db_session
from app.repositories.incidents import (
    AlertLinkError,
    create_incident,
    get_incident,
    get_incident_alert_ids,
    list_audit_events,
    list_incidents,
    set_incident_status,
)
from app.schemas.incident import (
    AuditEventRead,
    IncidentCreate,
    IncidentRead,
    IncidentStatusUpdate,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])
audit_router = APIRouter(prefix="/audit-events", tags=["audit"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Analyst = Annotated[
    Principal,
    Depends(require_roles("analyst", "admin")),
]
Admin = Annotated[Principal, Depends(require_roles("admin"))]


def _not_found(incident_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Incident {incident_id} was not found",
    )


async def _incident_response(
    session: AsyncSession,
    incident: Incident,
) -> IncidentRead:
    """Attach linked alert IDs to the incident response contract."""
    return IncidentRead(
        id=incident.id,
        title=incident.title,
        summary=incident.summary,
        severity=incident.severity,
        status=incident.status,
        created_by=incident.created_by,
        alert_ids=await get_incident_alert_ids(session, incident.id),
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_incident(
    data: IncidentCreate,
    session: Session,
    principal: Analyst,
) -> IncidentRead:
    """Group one or more unassigned alerts into an incident."""
    try:
        incident = await create_incident(
            session,
            data,
            actor=principal.actor,
        )
    except AlertLinkError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return await _incident_response(session, incident)


@router.get("", response_model=list[IncidentRead])
async def get_incidents(
    session: Session,
    _: Analyst,
) -> list[IncidentRead]:
    """List incidents newest first."""
    return [
        await _incident_response(session, incident)
        for incident in await list_incidents(session)
    ]


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident_by_id(
    incident_id: UUID,
    session: Session,
    _: Analyst,
) -> IncidentRead:
    """Retrieve one incident and its linked alert IDs."""
    incident = await get_incident(session, incident_id)
    if incident is None:
        raise _not_found(incident_id)
    return await _incident_response(session, incident)


@router.patch("/{incident_id}/status", response_model=IncidentRead)
async def update_incident_status(
    incident_id: UUID,
    update: IncidentStatusUpdate,
    session: Session,
    principal: Analyst,
) -> IncidentRead:
    """Move an incident through its small response lifecycle."""
    incident = await get_incident(session, incident_id)
    if incident is None:
        raise _not_found(incident_id)
    incident = await set_incident_status(
        session,
        incident,
        update.status,
        actor=principal.actor,
    )
    return await _incident_response(session, incident)


@audit_router.get("", response_model=list[AuditEventRead])
async def get_audit_events(
    session: Session,
    _: Admin,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AuditEventRead]:
    """Let administrators review the latest immutable change records."""
    return await list_audit_events(session, limit=limit)
