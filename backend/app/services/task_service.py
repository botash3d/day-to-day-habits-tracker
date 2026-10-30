import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate
from app.services.recurrence import next_due_date

COMPLETED_LIMIT = 100

_PRIORITY_RANK = case({"high": 0, "medium": 1, "low": 2}, value=Task.priority, else_=1)


class TaskNotFoundError(Exception):
    pass


class TaskCompletedError(Exception):
    pass


class TaskNotCompletedError(Exception):
    pass


class InvalidTaskError(Exception):
    pass


async def list_tasks(
    session: AsyncSession, user_id: uuid.UUID, status: str
) -> list[Task]:
    stmt = select(Task).where(Task.user_id == user_id)
    if status == "completed":
        stmt = (
            stmt.where(Task.completed_at.is_not(None))
            .order_by(Task.completed_at.desc())
            .limit(COMPLETED_LIMIT)
        )
    else:
        stmt = stmt.where(Task.completed_at.is_(None)).order_by(
            Task.due_date.is_(None),  # dated tasks first
            Task.due_date,
            _PRIORITY_RANK,
            Task.created_at,
        )
    return list(await session.scalars(stmt))


async def create_task(
    session: AsyncSession, user_id: uuid.UUID, data: TaskCreate
) -> Task:
    task = Task(user_id=user_id, **data.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def _get_owned(
    session: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    task = await session.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    if task is None:
        raise TaskNotFoundError
    return task


async def update_task(
    session: AsyncSession,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    changes: dict[str, Any],
) -> Task:
    task = await _get_owned(session, user_id, task_id)
    if task.completed_at is not None:
        raise TaskCompletedError
    for field, value in changes.items():
        setattr(task, field, value)
    if task.repeat != "none" and task.due_date is None:
        await session.rollback()
        raise InvalidTaskError("A repeating task needs a due date.")
    await session.commit()
    await session.refresh(task)
    return task


async def complete_task(
    session: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID, today: date
) -> Task:
    task = await _get_owned(session, user_id, task_id)
    if task.completed_at is not None:
        raise TaskCompletedError
    task.completed_at = datetime.now(UTC)
    if task.repeat != "none" and task.due_date is not None:
        session.add(
            Task(
                user_id=user_id,
                title=task.title,
                priority=task.priority,
                category=task.category,
                repeat=task.repeat,
                due_date=next_due_date(task.due_date, task.repeat, today),
            )
        )
        task.repeat = "none"  # this copy is finished; the new one carries the schedule
    await session.commit()
    await session.refresh(task)
    return task


async def reopen_task(
    session: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> Task:
    task = await _get_owned(session, user_id, task_id)
    if task.completed_at is None:
        raise TaskNotCompletedError
    task.completed_at = None
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(
    session: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> None:
    task = await _get_owned(session, user_id, task_id)
    await session.delete(task)
    await session.commit()