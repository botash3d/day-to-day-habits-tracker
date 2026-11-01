from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.schemas.learn import (
    LessonDetail,
    LessonProgressPublic,
    SubjectDetail,
    SubjectSummary,
)
from app.services import learn_service
from app.services.learn_service import LessonNotFoundError, SubjectNotFoundError

router = APIRouter(
    prefix="/learn",
    tags=["learn"],
    dependencies=[Depends(get_current_user)],
)

_SUBJECT_404 = "Subject not found."
_LESSON_404 = "Lesson not found."


@router.get("/subjects", response_model=list[SubjectSummary])
async def list_subjects(
    session: SessionDep, current_user: CurrentUser
) -> list[SubjectSummary]:
    return await learn_service.list_subjects(session, current_user.id)


@router.get("/subjects/{subject_slug}", response_model=SubjectDetail)
async def get_subject(
    subject_slug: str, session: SessionDep, current_user: CurrentUser
) -> SubjectDetail:
    try:
        return await learn_service.get_subject(session, current_user.id, subject_slug)
    except SubjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SUBJECT_404) from None


@router.get(
    "/subjects/{subject_slug}/lessons/{lesson_slug}", response_model=LessonDetail
)
async def get_lesson(
    subject_slug: str,
    lesson_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> LessonDetail:
    try:
        return await learn_service.get_lesson(
            session, current_user.id, subject_slug, lesson_slug
        )
    except SubjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SUBJECT_404) from None
    except LessonNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _LESSON_404) from None


@router.put(
    "/subjects/{subject_slug}/lessons/{lesson_slug}/progress",
    response_model=LessonProgressPublic,
)
async def complete_lesson(
    subject_slug: str,
    lesson_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> LessonProgressPublic:
    try:
        return await learn_service.mark_complete(
            session, current_user.id, subject_slug, lesson_slug
        )
    except SubjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SUBJECT_404) from None
    except LessonNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _LESSON_404) from None


@router.delete(
    "/subjects/{subject_slug}/lessons/{lesson_slug}/progress",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def uncomplete_lesson(
    subject_slug: str,
    lesson_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    try:
        await learn_service.mark_incomplete(
            session, current_user.id, subject_slug, lesson_slug
        )
    except SubjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SUBJECT_404) from None
    except LessonNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _LESSON_404) from None