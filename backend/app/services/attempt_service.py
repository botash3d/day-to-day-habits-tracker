import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.schemas.attempt import AttemptPublic


class AttemptNotFoundError(Exception):
    pass


class AttemptAlreadyFinishedError(Exception):
    pass


def _utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; PostgreSQL returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def to_public(attempt: Attempt) -> AttemptPublic:
    started = _utc(attempt.started_at)
    finished = _utc(attempt.finished_at) if attempt.finished_at else None
    if finished is not None and attempt.duration_seconds is not None:
        duration = attempt.duration_seconds
    else:
        end = finished or datetime.now(UTC)
        duration = max(0, int((end - started).total_seconds()))
    return AttemptPublic(
        id=attempt.id,
        problem_id=attempt.problem_id,
        started_at=started,
        finished_at=finished,
        solution_url=attempt.solution_url,
        duration_seconds=duration,
    )


async def get_active_attempt(
    session: AsyncSession, user_id: uuid.UUID, problem_id: int
) -> Attempt | None:
    return await session.scalar(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.problem_id == problem_id,
            Attempt.finished_at.is_(None),
        )
    )


async def start_attempt(
    session: AsyncSession, user_id: uuid.UUID, problem_id: int
) -> tuple[Attempt, bool]:
    """Return (attempt, created). Resumes the active attempt if there is one."""
    existing = await get_active_attempt(session, user_id, problem_id)
    if existing is not None:
        return existing, False

    attempt = Attempt(
        user_id=user_id, problem_id=problem_id, started_at=datetime.now(UTC)
    )
    session.add(attempt)
    try:
        await session.commit()
    except IntegrityError:
        # A concurrent request created the active attempt first.
        await session.rollback()
        existing = await get_active_attempt(session, user_id, problem_id)
        if existing is None:
            raise
        return existing, False
    await session.refresh(attempt)
    return attempt, True


async def _get_owned(
    session: AsyncSession, user_id: uuid.UUID, attempt_id: uuid.UUID
) -> Attempt:
    attempt = await session.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == user_id)
    )
    if attempt is None:
        raise AttemptNotFoundError
    return attempt


async def finish_attempt(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt_id: uuid.UUID,
    solution_url: str | None,
) -> Attempt:
    attempt = await _get_owned(session, user_id, attempt_id)
    if attempt.finished_at is not None:
        raise AttemptAlreadyFinishedError
    finished = datetime.now(UTC)
    attempt.finished_at = finished
    attempt.duration_seconds = max(
        0, int((finished - _utc(attempt.started_at)).total_seconds())
    )
    attempt.solution_url = solution_url
    await session.commit()
    await session.refresh(attempt)
    return attempt


async def discard_attempt(
    session: AsyncSession, user_id: uuid.UUID, attempt_id: uuid.UUID
) -> None:
    attempt = await _get_owned(session, user_id, attempt_id)
    if attempt.finished_at is not None:
        raise AttemptAlreadyFinishedError
    await session.delete(attempt)
    await session.commit()