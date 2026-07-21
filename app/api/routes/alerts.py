"""Alert validation API routes."""

from fastapi import APIRouter

from app.schemas.alert import AlertCreate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/validate", response_model=AlertCreate)
async def validate_alert(alert: AlertCreate) -> AlertCreate:
    """Validate and return an alert without persisting it."""

    return alert
