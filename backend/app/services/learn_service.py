import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learn import Exercise, Lesson, LessonProgress, Module, Subject
from app.schemas.learn import (
    ExercisePublic,
    ExerciseStep,
    LessonDetail,
    LessonProgressPublic,
    LessonSummary,
    ModulePublic,
    SubjectDetail,
    SubjectSummary,
)


class SubjectNotFoundError(Exception):
    pass


class LessonNotFoundError(Exception):
    pass

def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes, PostgreSQL returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@dataclass
class _Outline:
    subject: Subject
    # Visible lessons in course order, each with its module.
    entries: list[tuple[Module, Lesson]]
    # lesson_id -> when this user completed it.
    completed_at: dict[int, datetime]


async def _load_outline(
    session: AsyncSession, user_id: uuid.UUID, subject_slug: str
) -> _Outline:
    """Everything a student may see in one subject, in course order.

    A lesson is visible only if its subject, its module and the lesson itself
    are all published. Drafts are indistinguishable from missing content.
    """
    subject = await session.scalar(
        select(Subject).where(
            Subject.slug == subject_slug, Subject.is_published.is_(True)
        )
    )
    if subject is None:
        raise SubjectNotFoundError

    rows = await session.execute(
        select(Module, Lesson)
        .join(Lesson, Lesson.module_id == Module.id)
        .where(
            Module.subject_id == subject.id,
            Module.is_published.is_(True),
            Lesson.is_published.is_(True),
        )
        .order_by(Module.position, Module.id, Lesson.position, Lesson.id)
    )
    entries = [(module, lesson) for module, lesson in rows.all()]

    completed_at: dict[int, datetime] = {}
    lesson_ids = [lesson.id for _, lesson in entries]
    if lesson_ids:
        progress = await session.execute(
            select(LessonProgress.lesson_id, LessonProgress.completed_at).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
            )
        )
        completed_at = {
            lesson_id: _as_utc(when) for lesson_id, when in progress.tuples().all()
        }

    return _Outline(subject=subject, entries=entries, completed_at=completed_at)


def _find_index(outline: _Outline, lesson_slug: str) -> int:
    for index, (_, lesson) in enumerate(outline.entries):
        if lesson.slug == lesson_slug:
            return index
    raise LessonNotFoundError


async def list_subjects(
    session: AsyncSession, user_id: uuid.UUID
) -> list[SubjectSummary]:
    subjects = await session.scalars(
        select(Subject)
        .where(Subject.is_published.is_(True))
        .order_by(Subject.position, Subject.id)
    )
    visible = (Module.is_published.is_(True), Lesson.is_published.is_(True))

    totals_result = await session.execute(
        select(Module.subject_id, func.count(Lesson.id))
        .join(Lesson, Lesson.module_id == Module.id)
        .where(*visible)
        .group_by(Module.subject_id)
    )
    totals = dict(totals_result.tuples().all())

    done_result = await session.execute(
        select(Module.subject_id, func.count(Lesson.id))
        .join(Lesson, Lesson.module_id == Module.id)
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .where(LessonProgress.user_id == user_id, *visible)
        .group_by(Module.subject_id)
    )
    done = dict(done_result.tuples().all())

    return [
        SubjectSummary(
            slug=subject.slug,
            title=subject.title,
            description=subject.description,
            lesson_count=totals.get(subject.id, 0),
            completed_count=done.get(subject.id, 0),
        )
        for subject in subjects
    ]


async def get_subject(
    session: AsyncSession, user_id: uuid.UUID, subject_slug: str
) -> SubjectDetail:
    outline = await _load_outline(session, user_id, subject_slug)

    modules: list[ModulePublic] = []
    current_module_id: int | None = None
    for module, lesson in outline.entries:
        if module.id != current_module_id:
            modules.append(ModulePublic(slug=module.slug, title=module.title, lessons=[]))
            current_module_id = module.id
        modules[-1].lessons.append(
            LessonSummary(
                slug=lesson.slug,
                title=lesson.title,
                completed=lesson.id in outline.completed_at,
            )
        )

    next_lesson_slug = next(
        (
            lesson.slug
            for _, lesson in outline.entries
            if lesson.id not in outline.completed_at
        ),
        None,
    )
    return SubjectDetail(
        slug=outline.subject.slug,
        title=outline.subject.title,
        description=outline.subject.description,
        lesson_count=len(outline.entries),
        completed_count=len(outline.completed_at),
        modules=modules,
        next_lesson_slug=next_lesson_slug,
    )


async def get_lesson(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject_slug: str,
    lesson_slug: str,
) -> LessonDetail:
    outline = await _load_outline(session, user_id, subject_slug)
    index = _find_index(outline, lesson_slug)
    module, lesson = outline.entries[index]

    exercise_row = await session.scalar(
        select(Exercise).where(Exercise.lesson_id == lesson.id)
    )
    exercise = None
    if exercise_row is not None:
        exercise = ExercisePublic(
            kind=exercise_row.kind,
            steps=[ExerciseStep.model_validate(s) for s in exercise_row.steps],
        )

    return LessonDetail(
        slug=lesson.slug,
        title=lesson.title,
        body=lesson.body,
        subject_slug=outline.subject.slug,
        subject_title=outline.subject.title,
        module_slug=module.slug,
        module_title=module.title,
        completed=lesson.id in outline.completed_at,
        completed_at=outline.completed_at.get(lesson.id),
        previous_slug=outline.entries[index - 1][1].slug if index > 0 else None,
        next_slug=(
            outline.entries[index + 1][1].slug
            if index + 1 < len(outline.entries)
            else None
        ),
        exercise=exercise,
    )


async def mark_complete(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject_slug: str,
    lesson_slug: str,
) -> LessonProgressPublic:
    """Idempotent: completing an already completed lesson changes nothing."""
    outline = await _load_outline(session, user_id, subject_slug)
    _, lesson = outline.entries[_find_index(outline, lesson_slug)]

    row = await session.get(LessonProgress, (user_id, lesson.id))
    if row is None:
        row = LessonProgress(
            user_id=user_id, lesson_id=lesson.id, completed_at=datetime.now(UTC)
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError:
            # A parallel request completed it first. That is fine.
            await session.rollback()
            row = await session.get(LessonProgress, (user_id, lesson.id))

    return LessonProgressPublic(
        slug=lesson.slug,
        completed=row is not None,
        completed_at=_as_utc(row.completed_at) if row is not None else None,
    )


async def mark_incomplete(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject_slug: str,
    lesson_slug: str,
) -> None:
    """Idempotent: undoing a lesson that is not completed changes nothing."""
    outline = await _load_outline(session, user_id, subject_slug)
    _, lesson = outline.entries[_find_index(outline, lesson_slug)]

    row = await session.get(LessonProgress, (user_id, lesson.id))
    if row is not None:
        await session.delete(row)
        await session.commit()