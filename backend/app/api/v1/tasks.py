import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep, TimeZoneDep, get_current_user
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskPublic, TaskUpdate
from app.services import task_service as svc

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")


def _already_completed() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "This task is already completed.")


@router.get("", response_model=list[TaskPublic])
async def list_tasks(
    session: SessionDep,
    current_user: CurrentUser,
    task_status: Annotated[Literal["open", "completed"], Query(alias="status")] = "open",
) -> list[Task]:
    return await svc.list_tasks(session, current_user.id, task_status)


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, session: SessionDep, current_user: CurrentUser
) -> Task:
    return await svc.create_task(session, current_user.id, payload)


@router.patch("/{task_id}", response_model=TaskPublic)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Task:
    changes = payload.model_dump(exclude_unset=True)
    try:
        return await svc.update_task(session, current_user.id, task_id, changes)
    except svc.TaskNotFoundError:
        raise _not_found() from None
    except svc.TaskCompletedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Completed tasks cannot be edited."
        ) from None
    except svc.InvalidTaskError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/{task_id}/complete", response_model=TaskPublic)
async def complete_task(
    task_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    zone: TimeZoneDep,
) -> Task:
    today = datetime.now(UTC).astimezone(zone).date()
    try:
        return await svc.complete_task(session, current_user.id, task_id, today)
    except svc.TaskNotFoundError:
        raise _not_found() from None
    except svc.TaskCompletedError:
        raise _already_completed() from None


@router.post("/{task_id}/reopen", response_model=TaskPublic)
async def reopen_task(
    task_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Task:
    try:
        return await svc.reopen_task(session, current_user.id, task_id)
    except svc.TaskNotFoundError:
        raise _not_found() from None
    except svc.TaskNotCompletedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This task is not completed."
        ) from None


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> None:
    try:
        await svc.delete_task(session, current_user.id, task_id)
    except svc.TaskNotFoundError:
        raise _not_found() from None