"""Async SQLAlchemy engine and session lifecycle."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Expose the factory for background jobs and test overrides."""
    return async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session and release it afterward."""
    async with async_session_factory() as session:
        yield session
