import asyncio
from uuid import UUID

from app.db.models import Alert
from app.db.session import async_session_factory

ALERT_ID = UUID("fd833b23-26f5-4cb2-be9f-d14d73e9a883")
async def main() -> None:
    """Retrieve and display the first persisted alert."""
    async with async_session_factory() as session:
        retrieved_alert = await session.get(Alert, ALERT_ID)

    if retrieved_alert is None:
        raise RuntimeError(f"Alert {ALERT_ID} was not found")

    print(
        retrieved_alert.external_id,
        retrieved_alert.title,
        retrieved_alert.severity,
    )


if __name__ == "__main__":
    asyncio.run(main())