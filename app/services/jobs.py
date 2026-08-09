"""Small in-process background jobs for AI triage."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.repositories.alerts import get_alert, save_analysis
from app.repositories.jobs import get_analysis_job, set_job_state
from app.services.ai import (
    AIConfigurationError,
    AIServiceError,
    OpenAIAlertAnalyzer,
)

logger = logging.getLogger("uvicorn.error")


async def run_analysis_job(
    job_id: UUID,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Analyze one alert and persist a terminal job state.

    FastAPI runs this after returning the HTTP response. A production system
    with multiple replicas should replace this function with a durable queue.
    """
    async with session_factory() as session:
        job = await get_analysis_job(session, job_id)
        if job is None:
            return

        await set_job_state(session, job, status="running")
        alert = await get_alert(session, job.alert_id)
        if alert is None:
            await set_job_state(
                session,
                job,
                status="failed",
                error="Alert no longer exists",
            )
            return

        try:
            result = await OpenAIAlertAnalyzer(settings).analyze(alert)
            await save_analysis(
                session,
                alert,
                summary=result.summary,
                recommended_action=result.recommended_action,
                actor=job.requested_by,
            )
        except (AIConfigurationError, AIServiceError) as exc:
            await session.rollback()
            await set_job_state(
                session,
                job,
                status="failed",
                error=str(exc),
            )
            return
        except Exception:
            logger.exception(
                "Unexpected analysis job failure", extra={"job_id": job_id}
            )
            await session.rollback()
            await set_job_state(
                session,
                job,
                status="failed",
                error="Unexpected analysis failure",
            )
            return

        await set_job_state(session, job, status="completed")
