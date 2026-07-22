"""Async SQLAlchemy engine and session lifecycle."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

settings = Settings()

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


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session and release it afterward."""
    async with async_session_factory() as session:
        yield session


"""
FastAPI calls dependency
        ↓
Session created from pool
        ↓
yield gives session to route
        ↓
Route runs database operations
        ↓
Dependency resumes after request
        ↓
async with closes session
        ↓
Connection returns to pool
"""
