"""Authentication helpers shared by API routes."""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.repositories.users import get_user_by_id

api_key_header = APIKeyHeader(
    name="X-API-Key",
    description="API key configured through CIR_API_KEY.",
    auto_error=False,
)
bearer_scheme = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class Principal:
    """Authenticated caller identity used for authorization and auditing."""

    actor: str
    role: str
    user_id: UUID | None = None


def hash_password(password: str) -> str:
    """Hash a password with the current recommended password algorithm."""
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing hash details to callers."""
    return password_hash.verify(password, encoded_hash)


def create_access_token(
    *,
    user_id: UUID,
    username: str,
    role: str,
    settings: Settings,
) -> tuple[str, int]:
    """Create a signed, short-lived JWT for an authenticated user."""
    lifetime = timedelta(minutes=settings.access_token_minutes)
    expires_at = datetime.now(UTC) + lifetime
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return token, int(lifetime.total_seconds())


def _unauthorized() -> HTTPException:
    """Return a uniform authentication error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_principal(
    supplied_key: Annotated[str | None, Depends(api_key_header)],
    bearer: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Principal:
    """Authenticate either a machine API key or an analyst bearer token."""
    expected_key = settings.api_key.get_secret_value()
    if supplied_key is not None and secrets.compare_digest(
        supplied_key,
        expected_key,
    ):
        return Principal(actor="service-api-key", role="service")

    if bearer is None:
        raise _unauthorized()

    try:
        payload: dict[str, Any] = jwt.decode(
            bearer.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
        )
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized() from exc

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise _unauthorized()
    return Principal(
        actor=user.username,
        role=user.role,
        user_id=user.id,
    )


def require_roles(
    *allowed_roles: str,
) -> Callable[..., Any]:
    """Build a dependency that permits only the listed roles."""

    async def dependency(
        principal: Annotated[Principal, Depends(require_principal)],
    ) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency
