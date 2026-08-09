"""Database operations for analysis jobs."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisJob


async def create_analysis_job(
    session: AsyncSession,
    *,
    alert_id: UUID,
    requested_by: str,
) -> AnalysisJob:
    """Create a queued job that can be polled by clients."""
    job = AnalysisJob(
        alert_id=alert_id,
        requested_by=requested_by,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_analysis_job(
    session: AsyncSession,
    job_id: UUID,
) -> AnalysisJob | None:
    """Return one analysis job by primary key."""
    return await session.get(AnalysisJob, job_id)


async def set_job_state(
    session: AsyncSession,
    job: AnalysisJob,
    *,
    status: str,
    error: str | None = None,
) -> None:
    """Persist a job state transition."""
    job.status = status
    job.error = error
    await session.commit()
