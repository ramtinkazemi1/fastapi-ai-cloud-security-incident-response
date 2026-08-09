"""Alert ingestion and validation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import Principal, require_principal, require_roles
from app.db.models import Alert, AnalysisJob
from app.db.session import get_db_session, get_session_factory
from app.repositories.alerts import (
    DuplicateAlertError,
    get_alert,
    list_alerts,
    set_alert_status,
)
from app.repositories.alerts import (
    create_alert as persist_alert,
)
from app.repositories.jobs import create_analysis_job, get_analysis_job
from app.schemas.alert import (
    AlertCreate,
    AlertList,
    AlertRead,
    AlertSource,
    AlertStatus,
    AlertStatusUpdate,
)
from app.schemas.guardduty import GuardDutyFinding
from app.schemas.job import AnalysisJobRead
from app.schemas.wazuh import WazuhAlert
from app.services.guardduty import normalize_guardduty_finding
from app.services.jobs import run_analysis_job
from app.services.wazuh import normalize_wazuh_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

Session = Annotated[AsyncSession, Depends(get_db_session)]
SessionFactory = Annotated[
    async_sessionmaker[AsyncSession],
    Depends(get_session_factory),
]
Authenticated = Annotated[Principal, Depends(require_principal)]
Analyst = Annotated[
    Principal,
    Depends(require_roles("analyst", "admin")),
]


def _not_found(alert_id: UUID) -> HTTPException:
    """Build a consistent response for unknown alert identifiers."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert {alert_id} was not found",
    )


async def _persist_or_conflict(
    session: AsyncSession,
    alert_data: AlertCreate,
    *,
    actor: str,
) -> Alert:
    """Store an alert while presenting provider duplicates as HTTP 409."""
    try:
        return await persist_alert(session, alert_data, actor=actor)
    except DuplicateAlertError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An alert with this source and external_id already exists",
        ) from exc


@router.post("/validate", response_model=AlertCreate)
async def validate_alert(
    alert: AlertCreate,
    _: Authenticated,
) -> AlertCreate:
    """Validate and return an alert without persisting it."""

    return alert


@router.post(
    "",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert(
    alert_data: AlertCreate,
    session: Session,
    principal: Authenticated,
) -> Alert:
    """Validate and persist a security alert."""
    return await _persist_or_conflict(
        session,
        alert_data,
        actor=principal.actor,
    )


@router.post(
    "/ingest/guardduty",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_guardduty_finding(
    finding: GuardDutyFinding,
    session: Session,
    principal: Authenticated,
) -> Alert:
    """Normalize and persist one AWS GuardDuty finding."""
    alert_data = normalize_guardduty_finding(finding)
    return await _persist_or_conflict(
        session,
        alert_data,
        actor=principal.actor,
    )


@router.post(
    "/ingest/wazuh",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_wazuh_alert(
    wazuh_alert: WazuhAlert,
    session: Session,
    principal: Authenticated,
) -> Alert:
    """Normalize and persist one Wazuh alert."""
    return await _persist_or_conflict(
        session,
        normalize_wazuh_alert(wazuh_alert),
        actor=principal.actor,
    )


@router.get("", response_model=AlertList)
async def get_alerts(
    session: Session,
    _: Authenticated,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    source: AlertSource | None = None,
    alert_status: Annotated[
        AlertStatus | None,
        Query(alias="status"),
    ] = None,
    minimum_severity: Annotated[
        float | None,
        Query(ge=0, le=10),
    ] = None,
) -> AlertList:
    """List alerts with bounded pagination and optional filters."""
    items, total = await list_alerts(
        session,
        limit=limit,
        offset=offset,
        source=source,
        status=alert_status,
        minimum_severity=minimum_severity,
    )
    return AlertList(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert_by_id(
    alert_id: UUID,
    session: Session,
    _: Authenticated,
) -> Alert:
    """Retrieve one normalized alert."""
    db_alert = await get_alert(session, alert_id)
    if db_alert is None:
        raise _not_found(alert_id)
    return db_alert


@router.patch("/{alert_id}/status", response_model=AlertRead)
async def update_alert_status(
    alert_id: UUID,
    update: AlertStatusUpdate,
    session: Session,
    principal: Analyst,
) -> Alert:
    """Update the investigation state of an existing alert."""
    db_alert = await get_alert(session, alert_id)
    if db_alert is None:
        raise _not_found(alert_id)
    return await set_alert_status(
        session,
        db_alert,
        update.status,
        actor=principal.actor,
    )


@router.post(
    "/{alert_id}/analyze",
    response_model=AnalysisJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_alert(
    alert_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session,
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: SessionFactory,
    principal: Analyst,
) -> AnalysisJob:
    """Queue optional AI triage and return a pollable job."""
    db_alert = await get_alert(session, alert_id)
    if db_alert is None:
        raise _not_found(alert_id)

    job = await create_analysis_job(
        session,
        alert_id=db_alert.id,
        requested_by=principal.actor,
    )
    background_tasks.add_task(
        run_analysis_job,
        job.id,
        settings,
        session_factory,
    )
    return job


@router.get(
    "/analysis-jobs/{job_id}",
    response_model=AnalysisJobRead,
)
async def get_alert_analysis_job(
    job_id: UUID,
    session: Session,
    _: Analyst,
) -> AnalysisJob:
    """Poll a previously queued AI analysis job."""
    job = await get_analysis_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {job_id} was not found",
        )
    return job
