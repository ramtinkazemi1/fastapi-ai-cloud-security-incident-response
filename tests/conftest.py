"""Shared isolated database and HTTP client fixtures."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.session import get_db_session, get_session_factory
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Serve the API against a fresh in-memory database for each test."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "local-development-api-key"},
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient) -> AsyncClient:
    """Return a client authenticated as the bootstrapped administrator."""
    credentials = {
        "username": "admin",
        "password": "correct-horse-battery",
        "role": "admin",
    }
    bootstrap = await client.post(
        "/api/v1/auth/bootstrap",
        json=credentials,
    )
    assert bootstrap.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "username": credentials["username"],
            "password": credentials["password"],
        },
    )
    assert login.status_code == 200

    client.headers.pop("X-API-Key")
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client
