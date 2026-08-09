"""Tests for user authentication and role checks."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_bootstrap_login_and_identity(
    admin_client: AsyncClient,
) -> None:
    """The first administrator can authenticate and inspect their identity."""
    response = await admin_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_analyst_cannot_create_users(
    admin_client: AsyncClient,
) -> None:
    """Role checks prevent analysts from administering identities."""
    created = await admin_client.post(
        "/api/v1/auth/users",
        json={
            "username": "analyst",
            "password": "another-secure-password",
            "role": "analyst",
        },
    )
    assert created.status_code == 201

    login = await admin_client.post(
        "/api/v1/auth/login",
        json={
            "username": "analyst",
            "password": "another-secure-password",
        },
    )
    admin_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    denied = await admin_client.post(
        "/api/v1/auth/users",
        json={
            "username": "second-analyst",
            "password": "another-secure-password",
            "role": "analyst",
        },
    )

    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_invalid_login_is_rejected(client: AsyncClient) -> None:
    """Invalid credentials receive a generic authentication error."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": "wrong-password"},
    )

    assert response.status_code == 401
