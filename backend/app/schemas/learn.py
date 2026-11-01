from datetime import datetime

from pydantic import BaseModel


class ExerciseStep(BaseModel):
    # Defaults keep old rows readable if a field is ever added to the format.
    instruction: str = ""
    command: str = ""
    expected_output: str = ""
    check: str = ""


class ExercisePublic(BaseModel):
    kind: str
    steps: list[ExerciseStep]


class SubjectSummary(BaseModel):
    slug: str
    title: str
    description: str
    lesson_count: int
    completed_count: int


class LessonSummary(BaseModel):
    slug: str
    title: str
    completed: bool


class ModulePublic(BaseModel):
    slug: str
    title: str
    lessons: list[LessonSummary]


class SubjectDetail(SubjectSummary):
    modules: list[ModulePublic]
    # First lesson the user has not completed ("continue where you left off").
    # None when every lesson is done or the subject has no lessons yet.
    next_lesson_slug: str | None


class LessonDetail(BaseModel):
    slug: str
    title: str
    body: str
    subject_slug: str
    subject_title: str
    module_slug: str
    module_title: str
    completed: bool
    completed_at: datetime | None
    previous_slug: str | None
    next_slug: str | None
    exercise: ExercisePublic | None


class LessonProgressPublic(BaseModel):
    slug: str
    completed: bool
    completed_at: datetime | None