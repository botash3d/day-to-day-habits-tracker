from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.attempt import AttemptPublic


class ProblemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int | None
    slug: str
    title: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    topic: str
    part: str | None
    url: str


class ProblemWithStats(ProblemPublic):
    solve_count: int
    best_seconds: int | None
    last_solved_at: datetime | None


class ProblemDetail(ProblemPublic):
    active_attempt: AttemptPublic | None
    history: list[AttemptPublic]


class DsaStats(BaseModel):
    solved_problems: int
    total_problems: int
    total_attempts: int
    total_seconds: int