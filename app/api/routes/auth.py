"""User bootstrap, login, and administration routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    Principal,
    create_access_token,
    hash_password,
    require_principal,
    require_roles,
    verify_password,
)
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.users import (
    DuplicateUserError,
    count_users,
    create_user,
    get_user_by_username,
)
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserRole,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
Session = Annotated[AsyncSession, Depends(get_db_session)]


async def _create_user_or_conflict(
    session: AsyncSession,
    user_data: UserCreate,
    *,
    forced_role: UserRole | None = None,
) -> User:
    """Create a user while translating a duplicate username to HTTP 409."""
    try:
        return await create_user(
            session,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            role=forced_role or user_data.role,
        )
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc


@router.post(
    "/bootstrap",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_admin(
    user_data: UserCreate,
    session: Session,
    principal: Annotated[Principal, Depends(require_principal)],
) -> User:
    """Create the first administrator using the machine API key."""
    if principal.role != "service":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap requires the service API key",
        )
    if await count_users(session) != 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An administrator has already been bootstrapped",
        )
    return await _create_user_or_conflict(
        session,
        user_data,
        forced_role=UserRole.ADMIN,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    session: Session,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Exchange valid user credentials for a signed bearer token."""
    user = await get_user_by_username(session, credentials.username)
    if user is None or not verify_password(
        credentials.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
    )


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_user(
    user_data: UserCreate,
    session: Session,
    _: Annotated[Principal, Depends(require_roles("admin"))],
) -> User:
    """Allow an administrator to create an analyst or administrator."""
    return await _create_user_or_conflict(session, user_data)


@router.get("/me", response_model=UserRead)
async def get_current_user(
    session: Session,
    principal: Annotated[
        Principal,
        Depends(require_roles("analyst", "admin")),
    ],
) -> User:
    """Return the currently authenticated database user."""
    if principal.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A user token is required",
        )
    user = await session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user
