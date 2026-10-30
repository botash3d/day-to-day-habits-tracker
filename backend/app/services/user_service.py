import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    # Cheap early exit so we don't spend CPU hashing for a known duplicate.
    existing = await session.scalar(select(User.id).where(User.email == data.email))
    if existing is not None:
        raise EmailAlreadyRegisteredError

    hashed = await asyncio.to_thread(hash_password, data.password)
    user = User(email=data.email, full_name=data.full_name, hashed_password=hashed)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Lost a race with a concurrent signup for the same email.
        await session.rollback()
        raise EmailAlreadyRegisteredError from exc
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == email))
    hashed = user.hashed_password if user else DUMMY_HASH
    valid = await asyncio.to_thread(verify_password, password, hashed)
    if user is None or not valid:
        return None
    return user
