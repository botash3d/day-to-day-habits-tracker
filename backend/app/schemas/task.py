import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Priority = Literal["low", "medium", "high"]
Repeat = Literal["none", "daily", "weekly", "monthly"]


def _clean_title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("title must not be blank")
    return value


def _clean_category(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None
    priority: Priority = "medium"
    category: str | None = Field(default=None, max_length=50)
    repeat: Repeat = "none"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_title(value)

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str | None) -> str | None:
        return _clean_category(value)

    @model_validator(mode="after")
    def repeat_needs_due_date(self) -> "TaskCreate":
        if self.repeat != "none" and self.due_date is None:
            raise ValueError("A repeating task needs a due date.")
        return self


class TaskUpdate(BaseModel):
    """Only the fields that are sent get changed. Sending null clears due_date/category."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    priority: Priority | None = None
    category: str | None = Field(default=None, max_length=50)
    repeat: Repeat | None = None

    @field_validator("title", "priority", "repeat", mode="before")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("must not be null")
        return value

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_title(value)

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str | None) -> str | None:
        return _clean_category(value)


class TaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    due_date: date | None
    priority: Priority
    category: str | None
    repeat: Repeat
    completed_at: datetime | None
    created_at: datetime