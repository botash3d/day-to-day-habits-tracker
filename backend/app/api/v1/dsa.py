import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models.problem import Problem
from app.schemas.attempt import AttemptPublic, FinishAttempt
from app.schemas.problem import (
    DsaStats,
    ProblemDetail,
    ProblemPublic,
    ProblemWithStats,
)
from app.schemas.streak import StreakStats
from app.services.attempt_service import (
    AttemptAlreadyFinishedError,
    AttemptNotFoundError,
    discard_attempt,
    finish_attempt,
    get_active_attempt,
    start_attempt,
    to_public,
)
from app.services.dsa_stats import get_stats, list_history, list_problems_with_stats
from app.services.streaks import get_streaks

router = APIRouter(
    prefix="/dsa",
    tags=["dsa"],
    dependencies=[Depends(get_current_user)],
)


async def _require_problem(session: SessionDep, problem_id: int) -> Problem:
    problem = await session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    return problem


@router.get("/problems", response_model=list[ProblemWithStats])
async def list_problems(
    session: SessionDep, current_user: CurrentUser
) -> list[ProblemWithStats]:
    return await list_problems_with_stats(session, current_user.id)


@router.get("/stats", response_model=DsaStats)
async def dsa_stats(session: SessionDep, current_user: CurrentUser) -> DsaStats:
    return await get_stats(session, current_user.id)

@router.get("/streaks", response_model=StreakStats)
async def streaks(
    session: SessionDep, current_user: CurrentUser, tz: str = "UTC"
) -> StreakStats:
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise HTTPException(422, "Unknown timezone.") from None
    return await get_streaks(session, current_user.id, zone)

@router.get("/problems/{problem_id}", response_model=ProblemDetail)
async def get_problem(
    problem_id: int, session: SessionDep, current_user: CurrentUser
) -> ProblemDetail:
    problem = await _require_problem(session, problem_id)
    active = await get_active_attempt(session, current_user.id, problem_id)
    history = await list_history(session, current_user.id, problem_id)
    return ProblemDetail(
        **ProblemPublic.model_validate(problem).model_dump(),
        active_attempt=to_public(active) if active else None,
        history=[to_public(a) for a in history],
    )


@router.post(
    "/problems/{problem_id}/attempts",
    response_model=AttemptPublic,
    status_code=status.HTTP_201_CREATED,
)
async def start(
    problem_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    response: Response,
) -> AttemptPublic:
    await _require_problem(session, problem_id)
    attempt, created = await start_attempt(session, current_user.id, problem_id)
    if not created:
        response.status_code = status.HTTP_200_OK  # resumed an existing attempt
    return to_public(attempt)


@router.post("/attempts/{attempt_id}/finish", response_model=AttemptPublic)
async def finish(
    attempt_id: uuid.UUID,
    payload: FinishAttempt,
    session: SessionDep,
    current_user: CurrentUser,
) -> AttemptPublic:
    try:
        attempt = await finish_attempt(
            session, current_user.id, attempt_id, payload.solution_url
        )
    except AttemptNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found.") from None
    except AttemptAlreadyFinishedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This attempt is already finished."
        ) from None
    return to_public(attempt)


@router.delete("/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard(
    attempt_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> None:
    try:
        await discard_attempt(session, current_user.id, attempt_id)
    except AttemptNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found.") from None
    except AttemptAlreadyFinishedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Finished attempts cannot be discarded."
        ) from None

