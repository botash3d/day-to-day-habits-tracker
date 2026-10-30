import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AttemptPublic(BaseModel):
    id: uuid.UUID
    problem_id: int
    started_at: datetime
    finished_at: datetime | None
    solution_url: str | None
    # Elapsed time as computed by the server when this response was built.
    duration_seconds: int


class FinishAttempt(BaseModel):
    solution_url: str | None = Field(default=None, max_length=500)

    @field_validator("solution_url")
    @classmethod
    def must_be_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("solution_url must start with http:// or https://")
        return value