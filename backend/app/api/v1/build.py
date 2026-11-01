from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.schemas.build import (
    PageDetail,
    PageProgressPublic,
    ProjectDetail,
    ProjectSummary,
)
from app.services import build_service
from app.services.build_service import PageNotFoundError, ProjectNotFoundError

router = APIRouter(
    prefix="/build",
    tags=["build"],
    dependencies=[Depends(get_current_user)],
)

_PROJECT_404 = "Project not found."
_PAGE_404 = "Page not found."
_PAGE = "/projects/{project_slug}/modules/{module_slug}/pages/{page_slug}"


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(
    session: SessionDep, current_user: CurrentUser
) -> list[ProjectSummary]:
    return await build_service.list_projects(session, current_user.id)


@router.get("/projects/{project_slug}", response_model=ProjectDetail)
async def get_project(
    project_slug: str, session: SessionDep, current_user: CurrentUser
) -> ProjectDetail:
    try:
        return await build_service.get_project(session, current_user.id, project_slug)
    except ProjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PROJECT_404) from None


@router.get(_PAGE, response_model=PageDetail)
async def get_page(
    project_slug: str,
    module_slug: str,
    page_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> PageDetail:
    try:
        return await build_service.get_page(
            session, current_user.id, project_slug, module_slug, page_slug
        )
    except ProjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PROJECT_404) from None
    except PageNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PAGE_404) from None


@router.put(_PAGE + "/progress", response_model=PageProgressPublic)
async def complete_page(
    project_slug: str,
    module_slug: str,
    page_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> PageProgressPublic:
    try:
        return await build_service.mark_complete(
            session, current_user.id, project_slug, module_slug, page_slug
        )
    except ProjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PROJECT_404) from None
    except PageNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PAGE_404) from None


@router.delete(_PAGE + "/progress", status_code=status.HTTP_204_NO_CONTENT)
async def uncomplete_page(
    project_slug: str,
    module_slug: str,
    page_slug: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    try:
        await build_service.mark_incomplete(
            session, current_user.id, project_slug, module_slug, page_slug
        )
    except ProjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PROJECT_404) from None
    except PageNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _PAGE_404) from None