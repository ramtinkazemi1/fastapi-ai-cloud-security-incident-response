"""Database operations for application users."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.auth import UserRole


class DuplicateUserError(Exception):
    """Raised when a username already exists."""


async def count_users(session: AsyncSession) -> int:
    """Return the number of configured users."""
    return (await session.scalar(select(func.count()).select_from(User))) or 0


async def get_user_by_id(
    session: AsyncSession,
    user_id: UUID,
) -> User | None:
    """Return a user by primary key."""
    return await session.get(User, user_id)


async def get_user_by_username(
    session: AsyncSession,
    username: str,
) -> User | None:
    """Return a user by unique username."""
    return await session.scalar(
        select(User).where(User.username == username),
    )


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    password_hash: str,
    role: UserRole,
) -> User:
    """Persist a user and translate uniqueness conflicts."""
    user = User(
        username=username,
        password_hash=password_hash,
        role=role.value,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise DuplicateUserError from exc

    await session.refresh(user)
    return user
