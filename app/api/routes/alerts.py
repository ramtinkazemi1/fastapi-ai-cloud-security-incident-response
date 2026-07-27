"""Alert ingestion and validation API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert
from app.db.session import get_db_session
from app.schemas.alert import AlertCreate, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/validate", response_model=AlertCreate)
async def validate_alert(alert: AlertCreate) -> AlertCreate:
    """Validate and return an alert without persisting it."""

    return alert


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(alert_data: AlertCreate, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Alert:
    """Validate and persist a security alert."""
    db_alert = Alert(**alert_data.model_dump())

    session.add(db_alert)
    await session.commit()
    await session.refresh(db_alert)

    return db_alert
