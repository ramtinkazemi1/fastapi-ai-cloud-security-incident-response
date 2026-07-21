from fastapi import FastAPI
from app.core.config import Settings
from app.api.routes.alerts import router as alerts_router

settings = Settings()
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(
    alerts_router,
    prefix=settings.api_v1_prefix,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Confirm that the API process is running."""

    return {"status": "healthy"}
