import uuid

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.models.problem import Problem
from app.schemas.problem import DsaStats, ProblemPublic, ProblemWithStats


async def list_problems_with_stats(
    session: AsyncSession, user_id: uuid.UUID
) -> list[ProblemWithStats]:
    solves = (
        select(
            Attempt.problem_id.label("problem_id"),
            func.count(Attempt.id).label("solve_count"),
            func.min(Attempt.duration_seconds).label("best_seconds"),
            func.max(Attempt.finished_at).label("last_solved_at"),
        )
        .where(Attempt.user_id == user_id, Attempt.finished_at.is_not(None))
        .group_by(Attempt.problem_id)
        .subquery()
    )
    rows = await session.execute(
        select(
            Problem,
            solves.c.solve_count,
            solves.c.best_seconds,
            solves.c.last_solved_at,
        )
        .outerjoin(solves, solves.c.problem_id == Problem.id)
        .order_by(Problem.number.is_(None), Problem.number, Problem.id)
    )
    return [
        ProblemWithStats(
            **ProblemPublic.model_validate(problem).model_dump(),
            solve_count=solve_count or 0,
            best_seconds=best_seconds,
            last_solved_at=last_solved_at,
        )
        for problem, solve_count, best_seconds, last_solved_at in rows
    ]


async def list_history(
    session: AsyncSession, user_id: uuid.UUID, problem_id: int
) -> list[Attempt]:
    result = await session.scalars(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.problem_id == problem_id,
            Attempt.finished_at.is_not(None),
        )
        .order_by(Attempt.finished_at.desc())
    )
    return list(result)


async def get_stats(session: AsyncSession, user_id: uuid.UUID) -> DsaStats:
    total_problems = await session.scalar(select(func.count(Problem.id)))
    row = (
        await session.execute(
            select(
                func.count(distinct(Attempt.problem_id)),
                func.count(Attempt.id),
                func.coalesce(func.sum(Attempt.duration_seconds), 0),
            ).where(Attempt.user_id == user_id, Attempt.finished_at.is_not(None))
        )
    ).one()
    return DsaStats(
        solved_problems=row[0],
        total_problems=total_problems or 0,
        total_attempts=row[1],
        total_seconds=int(row[2]),
    )